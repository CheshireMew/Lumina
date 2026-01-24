# services/reporting/driver_state_collector.py
"""
[Refactor] 通用 Driver 状态收集器
提取自 stt_server._gather_stt_state() 和 tts_server._gather_tts_state() 的重复逻辑
"""
import logging
from typing import List, Dict, Any

logger = logging.getLogger("DriverStateCollector")


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
            runtime_target: 运行目标 (e.g. "stt_server", "tts_server")
            service_url: 服务切换 URL
            
        Returns:
            包含所有 Driver 状态的列表，符合 PluginState Schema
        """
        plugins = []
        
        if not manager:
            return plugins
        
        active_driver = getattr(manager, 'active_driver_id', None)
        drivers = getattr(manager, 'drivers', {})
        
        for pid, driver in drivers.items():
            is_active = (pid == active_driver)
            
            # [Architecture 6.0] Active Status Reporting
            status = "stopped"
            if is_active:
                status = getattr(manager, 'loading_status', 'idle')
                if status == "idle":
                    status = "ready"
            
            # Extract metadata from driver instance
            driver_name = getattr(driver, 'name', pid)
            driver_desc = getattr(driver, 'description', '')
            
            plugins.append({
                "id": pid,
                "name": driver_name,
                "description": driver_desc,
                "category": category,
                "group_id": category,
                "enabled": is_active,
                "active_status": status,
                "active_in_group": is_active,
                "runtime_target": runtime_target,
                "is_driver": True,
                "service_url": service_url,
                "driver_id": pid
            })
        
        return plugins
