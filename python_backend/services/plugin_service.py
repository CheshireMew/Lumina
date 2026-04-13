"""
PluginService (SDK 版本)
========================

基于新 SDK 架构的插件服务 Facade。
简化了旧版的复杂依赖（移除 PluginRegistry/PluginController）。
"""

import logging
from typing import List, Dict, Any, Optional

from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target

# from app_config import config as app_config  # Removed global import

logger = logging.getLogger("PluginService")


class PluginService:
    """
    [SDK 版本] 插件服务 Facade
    
    提供插件系统的 API 接口，供路由层调用。
    """
    
    def __init__(self, services_container):
        self.services = services_container
        self._plugin_cache: Dict[str, Dict] = {}
        from services.capability_inventory import CapabilityInventoryService
        self.inventory = CapabilityInventoryService(services_container)

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
    
    # ================= 插件列表 =================
    
    async def list_all_plugins(self) -> List[Dict[str, Any]]:
        """获取所有插件列表（聚合 Main + Worker）"""
        aggregator = getattr(self.services, 'plugin_state_aggregator', None)
        if aggregator:
            snapshot = aggregator.get_snapshot()
            if snapshot:
                return snapshot

        spm = getattr(self.services, 'system_plugin_manager', None)
        if spm:
            return spm.list_plugins()
        return []
    
    # ================= 插件控制 =================
    
    async def toggle_plugin(self, plugin_id: str, target_state: bool = None) -> Dict[str, Any]:
        """
        切换插件状态
        
        Args:
            plugin_id: 插件 ID
            target_state: 目标状态，None 表示切换
        
        Returns:
            操作结果
        """
        spm = getattr(self.services, 'system_plugin_manager', None)
        if not spm:
            return {"success": False, "error": "Plugin system not available"}
        aggregator = getattr(self.services, 'plugin_state_aggregator', None)
        
        # 确定目标状态
        plugin = spm.get_plugin(plugin_id)
        current_state = getattr(plugin, "enabled", False) if plugin else False
        runtime_state = aggregator.get_plugin(plugin_id) if aggregator else None
        
        if target_state is None:
            target_state = not current_state
        
        try:
            from services.config_service import ConfigService

            config = self.services.config
            config_service = ConfigService(self.services)
            runtime_target = self._resolve_runtime_target(plugin_id, runtime_state)
            if target_state:
                if plugin:
                    await spm.enable_plugin(plugin_id)
                else:
                    from services.infra.worker_control_hub import get_worker_control_hub
                    config_service.set_plugin_desired_state(plugin_id, True)
                    capability_key = (runtime_state or {}).get("group_id")
                    if capability_key and (runtime_state or {}).get("kind") == "provider":
                        config_service.set_selected_provider(capability_key, plugin_id)
                    if not self._ensure_worker_runtime(runtime_target):
                        return {"success": False, "error": f"Runtime {runtime_target} is unavailable"}
                    await get_worker_control_hub().broadcast_lifecycle(
                        "enable",
                        plugin_id,
                        runtime_target=runtime_target,
                    )
            else:
                if plugin:
                    await spm.disable_plugin(plugin_id)
                else:
                    from services.infra.worker_control_hub import get_worker_control_hub
                    config_service.set_plugin_desired_state(plugin_id, False)
                    capability_key = (runtime_state or {}).get("group_id")
                    if capability_key and (runtime_state or {}).get("kind") == "provider" and config.get_selected_provider(capability_key) == plugin_id:
                        config_service.clear_selected_provider(capability_key)
                    await get_worker_control_hub().broadcast_lifecycle(
                        "disable",
                        plugin_id,
                        runtime_target=runtime_target,
                    )

            logger.info(f"🔌 Plugin {plugin_id} -> {'enabled' if target_state else 'disabled'}")

            event_bus = getattr(self.services, "event_bus", None)
            if event_bus:
                await event_bus.emit(
                    "plugin_status",
                    {
                        "plugin_id": plugin_id,
                        "status": "enabled" if target_state else "disabled",
                    },
                    source="plugin.service",
                )
            
            return {
                "success": True,
                "plugin_id": plugin_id,
                "enabled": target_state
            }
            
        except Exception as e:
            logger.error(f"Failed to toggle plugin: {e}")
            return {"success": False, "error": str(e)}
    
    async def update_config(self, plugin_id: str, key: str, value: Any) -> Dict[str, Any]:
        """更新插件配置"""
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
    
    # ================= UI 插槽 =================
    
    async def get_all_ui_slots(self) -> List[Dict[str, Any]]:
        """获取所有 UI 插槽"""
        from services.plugin_kernel.state_builder import normalize_ui_slot

        slots: List[Dict[str, Any]] = []
        for plugin in await self.list_all_plugins():
            if not plugin.get("active"):
                continue
            for slot in plugin.get("ui_slots", []) or []:
                normalized = normalize_ui_slot(slot, plugin["id"])
                if normalized:
                    slots.append(normalized)
        return slots

    async def get_capability_catalog(self) -> List[Dict[str, Any]]:
        return self.inventory.list_capabilities()

    async def get_debug_snapshot(self) -> Dict[str, Any]:
        return await self.inventory.build_debug_snapshot()

    async def get_marketplace_snapshot(self) -> Dict[str, Any]:
        return self.inventory.marketplace_snapshot()

    async def install_plugin_from_zip(self, file_obj, filename: str | None = None) -> Dict[str, Any]:
        return await self.inventory.install_plugin_from_zip(file_obj, filename)
    
    @property
    def system_plugin_manager(self):
        return getattr(self.services, 'system_plugin_manager', None)

    def update_group_assignment(self, plugin_id: str, group_id: str) -> str:
        self.services.config.plugin_groups.assignments[plugin_id] = group_id
        self.services.config.save()
        return group_id

    def update_category_assignment(self, plugin_id: str, category: str) -> str:
        self.services.config.plugin_groups.custom_categories[plugin_id] = category
        self.services.config.save()
        return category

    def update_group_behavior(self, group_id: str, behavior: str) -> str:
        self.services.config.plugin_groups.group_behaviors[group_id] = behavior
        self.services.config.save()
        return behavior
