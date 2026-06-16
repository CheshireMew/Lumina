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
        
        normalized_target = normalize_runtime_target(runtime_target)

        for pid, _driver in manager.iter_drivers():
            state = manager.snapshot_provider_state(pid)
            desired_enabled = bool(state["desired_enabled"])
            active_status = state["active_status"]
            plugins.append({
                **state,
                "kind": "provider",
                "category": category,
                "group_id": category,
                "group_policy": "exclusive",
                "capabilities": [category],
                "computed_status": _compute_provider_status(desired_enabled, active_status),
                "runtime_target": normalized_target,
                "service_url": service_url,
            })
        
        return plugins
