import asyncio
import logging
from typing import Any, Dict

from core.runtime import (
    MAIN_RUNTIME_TARGET,
    get_capability_contract,
    normalize_runtime_target,
)

logger = logging.getLogger("ProviderConfigService")


class ProviderConfigService:
    """Internal support for provider config propagation and worker lifecycle."""

    def __init__(self, *, config, process_manager, worker_control_hub, config_service):
        self.config = config
        self.process_manager = process_manager
        self.worker_control_hub = worker_control_hub
        self.config_service = config_service

    def _resolve_runtime_target(self, provider_id: str, runtime_state: Dict[str, Any] | None) -> str:
        runtime_target = (runtime_state or {}).get("runtime_target")
        if runtime_target:
            return normalize_runtime_target(runtime_target)

        parts = provider_id.split(".", 2)
        capability = parts[1] if len(parts) == 3 and parts[0] == "driver" else ""
        contract = get_capability_contract(capability)
        if contract:
            return normalize_runtime_target(contract.worker_runtime_target)
        return MAIN_RUNTIME_TARGET

    def _ensure_worker_runtime(self, runtime_target: str) -> bool:
        normalized_target = normalize_runtime_target(runtime_target)
        if normalized_target == MAIN_RUNTIME_TARGET:
            return True

        if self.process_manager.is_running(normalized_target):
            return True
        return self.process_manager.start_worker(normalized_target)

    async def ensure_worker_running(self, runtime_target: str) -> bool:
        return await asyncio.to_thread(self._ensure_worker_runtime, runtime_target)

    async def update_config(self, provider_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Propagate provider configuration to its owning runtime."""
        try:
            config = self.config
            old_value = config.capabilities.settings.get(provider_id, {}).get(key)

            runtime_target = self._resolve_runtime_target(provider_id, None)

            if runtime_target != MAIN_RUNTIME_TARGET:
                if not await asyncio.to_thread(self._ensure_worker_runtime, runtime_target):
                    return {"success": False, "error": f"Runtime {runtime_target} is unavailable"}

                next_settings = dict(config.capabilities.settings.get(provider_id, {}))
                next_settings[key] = value
                await self.worker_control_hub.broadcast_config_update(
                    data={
                        "provider_id": provider_id,
                        "key": key,
                        "value": value,
                        "settings": next_settings,
                    },
                    section=f"provider:{provider_id}",
                    runtime_target=runtime_target,
                )

            try:
                self.config_service.set_provider_setting(provider_id, key, value)
            except Exception:
                if runtime_target != MAIN_RUNTIME_TARGET:
                    await self.worker_control_hub.broadcast_config_update(
                        data={
                            "provider_id": provider_id,
                            "key": key,
                            "value": old_value,
                        },
                        section=f"provider:{provider_id}:rollback",
                        runtime_target=runtime_target,
                    )
                raise

            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return {"success": False, "error": str(e)}
