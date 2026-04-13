# services/reporting/driver_state_collector.py
"""
[Refactor] 通用 Driver 状态收集器
提取自 STT/TTS capability 状态汇报中的重复逻辑
"""
import logging
from typing import List, Dict, Any

from core.runtime import normalize_runtime_target

logger = logging.getLogger("DriverStateCollector")


def _compute_provider_status(desired_enabled: bool, active_status: str) -> str:
    if desired_enabled:
        if active_status in {"ready", "idle", "running"}:
            return "running"
        if active_status in {"loading", "transitioning", "starting"}:
            return "provisioning"
        if active_status == "error":
            return "error"
        if active_status == "offline":
            return "offline"
        return "stuck"

    if active_status in {"ready", "idle", "running"}:
        return "stopping"
    if active_status == "offline":
        return "offline"
    return "stopped"


class DriverStateCollector:
    """
    通用工具类：从 PluginManager 收集 Driver 状态用于 WorkerStatusReporter。
    消除 STT/TTS Server 中的代码重复。
    """
    
    @staticmethod
    def gather_driver_states(
        manager,
        category: str,
        runtime_target: str,
        service_url: str
    ) -> List[Dict[str, Any]]:
        """
        从 Manager 中收集所有 Driver 的状态信息。
        
        Args:
            manager: STTPluginManager 或 TTSPluginManager 实例
            category: 插件类别 (e.g. "stt", "tts")
            runtime_target: 运行目标 (e.g. "worker:stt", "worker:tts")
            service_url: 服务切换 URL
            
        Returns:
            包含所有 Driver 状态的列表，符合 PluginState Schema
        """
        plugins = []
        
        if not manager:
            return plugins
        
        active_driver = getattr(manager, 'active_driver_id', None)
        active_driver_instance = getattr(manager, "active_driver", None)
        drivers = getattr(manager, 'drivers', {})
        normalized_target = normalize_runtime_target(runtime_target)
        config = getattr(manager, "config", None)

        for pid, driver in drivers.items():
            is_active = (pid == active_driver and active_driver_instance is not None)
            desired_enabled = (
                bool(config.is_plugin_desired_enabled(pid))
                if config and hasattr(config, "is_plugin_desired_enabled")
                else is_active
            )
            
            # [Architecture 6.0] Active Status Reporting
            status = "stopped"
            if is_active:
                status = getattr(manager, 'loading_status', 'idle')
                if status == "idle":
                    status = "ready"
            active = is_active and status in {"ready", "idle", "running"}
            
            # Extract metadata from driver instance
            driver_name = getattr(driver, 'name', pid)
            driver_desc = getattr(driver, 'description', '')
            current_config = {}
            if config and hasattr(config, "plugins"):
                current_config = dict(config.plugins.settings.get(pid, {}))
            
            plugins.append({
                "id": pid,
                "name": driver_name,
                "description": driver_desc,
                "kind": "provider",
                "category": category,
                "group_id": category,
                "group_policy": "exclusive",
                "capabilities": [category],
                "enabled": desired_enabled,
                "desired_enabled": desired_enabled,
                "active": active,
                "active_status": status,
                "computed_status": _compute_provider_status(desired_enabled, status),
                "active_in_group": is_active,
                "runtime_target": normalized_target,
                "permissions": list(getattr(driver, "permissions", []) or []),
                "config_schema": getattr(driver, "config_schema", None),
                "current_config": current_config,
                "is_driver": True,
                "service_url": service_url,
                "driver_id": pid,
                "error": getattr(manager, "last_error", None) if is_active else None,
                "load_time_ms": getattr(manager, "last_load_duration_ms", None) if is_active else None,
            })
        
        return plugins
