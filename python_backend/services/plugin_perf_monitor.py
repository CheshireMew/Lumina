"""
Plugin Performance Monitor

Monitors plugin execution times and provides observability into plugin health.
Helps identify slow or problematic plugins.

Features:
- Initialization time tracking
- Event handler execution time monitoring
- Timeout warnings
- Performance summary reports
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Callable, Any
from dataclasses import dataclass, field
from collections import defaultdict

logger = logging.getLogger("PluginPerfMonitor")


@dataclass
class PluginMetrics:
    """Performance metrics for a single plugin"""
    plugin_id: str
    init_time_ms: float = 0.0
    total_calls: int = 0
    total_time_ms: float = 0.0
    max_time_ms: float = 0.0
    timeout_count: int = 0
    error_count: int = 0
    last_call_time: float = 0.0
    _call_times: list = field(default_factory=list)
    
    @property
    def avg_time_ms(self) -> float:
        if self.total_calls == 0:
            return 0.0
        return self.total_time_ms / self.total_calls


class PluginPerfMonitor:
    """
    Centralized plugin performance monitoring.
    
    Usage:
        monitor = PluginPerfMonitor()
        
        # Track initialization
        with monitor.track_init("my_plugin"):
            plugin.initialize(context)
        
        # Track event handler
        async with monitor.track_async("my_plugin", "on_tick"):
            await handler(event)
        
        # Get report
        report = monitor.get_report()
    """
    
    # Thresholds
    INIT_WARNING_MS = 1000      # 1 second
    HANDLER_WARNING_MS = 100    # 100ms
    HANDLER_TIMEOUT_MS = 5000   # 5 seconds
    
    def __init__(self):
        self._metrics: Dict[str, PluginMetrics] = {}
        self._enabled = True
    
    def _get_or_create(self, plugin_id: str) -> PluginMetrics:
        if plugin_id not in self._metrics:
            self._metrics[plugin_id] = PluginMetrics(plugin_id=plugin_id)
        return self._metrics[plugin_id]
    
    class InitTracker:
        """Context manager for tracking initialization time"""
        def __init__(self, monitor: 'PluginPerfMonitor', plugin_id: str):
            self.monitor = monitor
            self.plugin_id = plugin_id
            self.start_time = 0.0
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            metrics = self.monitor._get_or_create(self.plugin_id)
            metrics.init_time_ms = elapsed_ms
            
            if elapsed_ms > self.monitor.INIT_WARNING_MS:
                logger.warning(
                    f"🐢 Slow plugin init: {self.plugin_id} took {elapsed_ms:.0f}ms "
                    f"(threshold: {self.monitor.INIT_WARNING_MS}ms)"
                )
            else:
                logger.debug(f"⚡ Plugin {self.plugin_id} initialized in {elapsed_ms:.1f}ms")
            
            if exc_type:
                metrics.error_count += 1
            
            return False  # Don't suppress exceptions
    
    def track_init(self, plugin_id: str) -> InitTracker:
        """Track plugin initialization time"""
        return self.InitTracker(self, plugin_id)
    
    class AsyncTracker:
        """Async context manager for tracking handler execution"""
        def __init__(self, monitor: 'PluginPerfMonitor', plugin_id: str, handler_name: str):
            self.monitor = monitor
            self.plugin_id = plugin_id
            self.handler_name = handler_name
            self.start_time = 0.0
        
        async def __aenter__(self):
            self.start_time = time.perf_counter()
            return self
        
        async def __aexit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            metrics = self.monitor._get_or_create(self.plugin_id)
            
            metrics.total_calls += 1
            metrics.total_time_ms += elapsed_ms
            metrics.last_call_time = time.time()
            
            if elapsed_ms > metrics.max_time_ms:
                metrics.max_time_ms = elapsed_ms
            
            # Keep last 100 call times for percentile calculation
            metrics._call_times.append(elapsed_ms)
            if len(metrics._call_times) > 100:
                metrics._call_times.pop(0)
            
            if elapsed_ms > self.monitor.HANDLER_TIMEOUT_MS:
                metrics.timeout_count += 1
                logger.error(
                    f"🚨 Plugin timeout: {self.plugin_id}.{self.handler_name}() "
                    f"took {elapsed_ms:.0f}ms (limit: {self.monitor.HANDLER_TIMEOUT_MS}ms)"
                )
            elif elapsed_ms > self.monitor.HANDLER_WARNING_MS:
                logger.warning(
                    f"🐢 Slow handler: {self.plugin_id}.{self.handler_name}() "
                    f"took {elapsed_ms:.0f}ms"
                )
            
            if exc_type:
                metrics.error_count += 1
            
            return False
    
    def track_async(self, plugin_id: str, handler_name: str = "handler") -> AsyncTracker:
        """Track async handler execution time"""
        return self.AsyncTracker(self, plugin_id, handler_name)
    
    class SyncTracker:
        """Sync context manager for tracking handler execution"""
        def __init__(self, monitor: 'PluginPerfMonitor', plugin_id: str, handler_name: str):
            self.monitor = monitor
            self.plugin_id = plugin_id
            self.handler_name = handler_name
            self.start_time = 0.0
        
        def __enter__(self):
            self.start_time = time.perf_counter()
            return self
        
        def __exit__(self, exc_type, exc_val, exc_tb):
            elapsed_ms = (time.perf_counter() - self.start_time) * 1000
            metrics = self.monitor._get_or_create(self.plugin_id)
            
            metrics.total_calls += 1
            metrics.total_time_ms += elapsed_ms
            metrics.last_call_time = time.time()
            
            if elapsed_ms > metrics.max_time_ms:
                metrics.max_time_ms = elapsed_ms
            
            if elapsed_ms > self.monitor.HANDLER_WARNING_MS:
                logger.warning(
                    f"🐢 Slow handler: {self.plugin_id}.{self.handler_name}() "
                    f"took {elapsed_ms:.0f}ms"
                )
            
            if exc_type:
                metrics.error_count += 1
            
            return False
    
    def track_sync(self, plugin_id: str, handler_name: str = "handler") -> SyncTracker:
        """Track sync handler execution time"""
        return self.SyncTracker(self, plugin_id, handler_name)
    
    def record_error(self, plugin_id: str):
        """Record an error for a plugin"""
        self._get_or_create(plugin_id).error_count += 1
    
    def get_metrics(self, plugin_id: str) -> Optional[PluginMetrics]:
        """Get metrics for a specific plugin"""
        return self._metrics.get(plugin_id)
    
    def get_report(self) -> Dict[str, Any]:
        """Generate a performance report for all plugins"""
        plugins = []
        total_init_time = 0.0
        slow_plugins = []
        error_plugins = []
        
        for pid, m in self._metrics.items():
            total_init_time += m.init_time_ms
            
            plugin_info = {
                "id": pid,
                "init_ms": round(m.init_time_ms, 1),
                "calls": m.total_calls,
                "avg_ms": round(m.avg_time_ms, 2),
                "max_ms": round(m.max_time_ms, 1),
                "timeouts": m.timeout_count,
                "errors": m.error_count,
            }
            plugins.append(plugin_info)
            
            if m.avg_time_ms > self.HANDLER_WARNING_MS:
                slow_plugins.append(pid)
            if m.error_count > 0:
                error_plugins.append(pid)
        
        # Sort by total time descending
        plugins.sort(key=lambda x: x["avg_ms"] * x["calls"], reverse=True)
        
        return {
            "total_plugins": len(self._metrics),
            "total_init_time_ms": round(total_init_time, 1),
            "slow_plugins": slow_plugins,
            "error_plugins": error_plugins,
            "plugins": plugins,
        }
    
    def get_summary(self) -> str:
        """Get a human-readable summary"""
        report = self.get_report()
        lines = [
            f"📊 Plugin Performance Summary",
            f"   Total plugins: {report['total_plugins']}",
            f"   Total init time: {report['total_init_time_ms']}ms",
        ]
        
        if report['slow_plugins']:
            lines.append(f"   ⚠️ Slow plugins: {', '.join(report['slow_plugins'])}")
        if report['error_plugins']:
            lines.append(f"   ❌ Error plugins: {', '.join(report['error_plugins'])}")
        
        return "\n".join(lines)


# Global instance
_monitor: Optional[PluginPerfMonitor] = None


def get_perf_monitor() -> PluginPerfMonitor:
    """Get or create the global performance monitor"""
    global _monitor
    if _monitor is None:
        _monitor = PluginPerfMonitor()
    return _monitor
