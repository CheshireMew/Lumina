import logging
from typing import Any, Dict

from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target

logger = logging.getLogger("PluginService")


class PluginService:
    """Internal support for provider config propagation and worker lifecycle."""

    def __init__(self, services_container):
        self.services = services_container

    def _resolve_runtime_target(self, plugin_id: str, runtime_state: Dict[str, Any] | None) -> str:
        runtime_target = (runtime_state or {}).get("runtime_target")
        if runtime_target:
            return normalize_runtime_target(runtime_target)

        spm = getattr(self.services, "system_plugin_manager", None)
        manifest = spm.get_manifest(plugin_id) if spm else None
        return normalize_runtime_target(getattr(manifest, "runtime_target", MAIN_RUNTIME_TARGET))

    def _ensure_worker_runtime(self, runtime_target: str) -> bool:
        normalized_target = normalize_runtime_target(runtime_target)
        if normalized_target == MAIN_RUNTIME_TARGET:
            return True

        process_manager = self.services.get_process_manager()
        if not process_manager:
            return False
        if process_manager.is_running(normalized_target):
            return True
        return process_manager.start_worker(normalized_target)

    async def ensure_worker_running(self, runtime_target: str) -> bool:
        return self._ensure_worker_runtime(runtime_target)

    async def update_config(self, plugin_id: str, key: str, value: Any) -> Dict[str, Any]:
        """Propagate provider configuration to its owning runtime."""
        try:
            from services.config_service import ConfigService

            config = self.services.config
            ConfigService(self.services).set_plugin_setting(plugin_id, key, value)

            aggregator = getattr(self.services, "plugin_state_aggregator", None)
            runtime_state = aggregator.get_plugin(plugin_id) if aggregator else None
            runtime_target = self._resolve_runtime_target(plugin_id, runtime_state)

            if runtime_target != MAIN_RUNTIME_TARGET:
                from services.infra.worker_control_hub import get_worker_control_hub

                if not self._ensure_worker_runtime(runtime_target):
                    return {"success": False, "error": f"Runtime {runtime_target} is unavailable"}

                await get_worker_control_hub().broadcast_config_update(
                    data={
                        "plugin_id": plugin_id,
                        "key": key,
                        "value": value,
                        "settings": dict(config.plugins.settings.get(plugin_id, {})),
                    },
                    section=f"plugin:{plugin_id}",
                    runtime_target=runtime_target,
                )
            
            return {"success": True}
            
        except Exception as e:
            logger.error(f"Failed to update config: {e}")
            return {"success": False, "error": str(e)}

    @property
    def system_plugin_manager(self):
        return getattr(self.services, 'system_plugin_manager', None)
