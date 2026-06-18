import logging
from typing import Any, Dict

from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target, runtime_target_for_capability

logger = logging.getLogger("ProviderConfigService")


class ProviderConfigService:
    """Internal support for provider config propagation and worker lifecycle."""

    def __init__(self, services_container):
        self.services = services_container

    def _resolve_runtime_target(self, provider_id: str, runtime_state: Dict[str, Any] | None) -> str:
        runtime_target = (runtime_state or {}).get("runtime_target")
        if runtime_target:
            return normalize_runtime_target(runtime_target)

        if provider_id.startswith("driver.stt."):
            return runtime_target_for_capability("stt")
        if provider_id.startswith("driver.tts."):
            return runtime_target_for_capability("tts")
        if provider_id.startswith("driver.vision."):
            return runtime_target_for_capability("vision")
        return MAIN_RUNTIME_TARGET

    def _ensure_worker_runtime(self, runtime_target: str) -> bool:
        normalized_target = normalize_runtime_target(runtime_target)
        if normalized_target == MAIN_RUNTIME_TARGET:
            return True

        process_manager = self.services.get_process_manager()
        if process_manager.is_running(normalized_target):
            return True
        return process_manager.start_worker(normalized_target)

    async def ensure_worker_running(self, runtime_target: str) -> bool:
        return self._ensure_worker_runtime(runtime_target)

    async def update_config(self, provider_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Propagate provider configuration to its owning runtime."""
        try:
            from services.config_service import ConfigService

            config = self.services.get_config()
            ConfigService(self.services).set_provider_setting(provider_id, key, value)

            runtime_target = self._resolve_runtime_target(provider_id, None)

            if runtime_target != MAIN_RUNTIME_TARGET:
                from services.infra.worker_control_hub import get_worker_control_hub

                if not self._ensure_worker_runtime(runtime_target):
                    return {"success": False, "error": f"Runtime {runtime_target} is unavailable"}

                await get_worker_control_hub().broadcast_config_update(
                    data={
                        "provider_id": provider_id,
                        "key": key,
                        "value": value,
                        "settings": dict(config.capabilities.settings.get(provider_id, {})),
                    },
                    section=f"provider:{provider_id}",
                    runtime_target=runtime_target,
                )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return {"success": False, "error": str(e)}
