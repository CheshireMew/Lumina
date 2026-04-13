"""
Log 模块
========

插件日志功能。

Example:
    lumina.log.info("操作完成")
    lumina.log.error("发生错误", exc_info=True)
"""

import logging
from typing import Optional


class LogModule:
    """
    日志模块
    
    提供插件专属的日志记录功能。
    """
    
    def __init__(self, container):
        self._container = container
        self._logger: Optional[logging.Logger] = None
        self._plugin_id: Optional[str] = None
    
    def _set_plugin_context(self, plugin_id: str):
        """由系统调用，设置插件上下文"""
        self._plugin_id = plugin_id
        self._logger = logging.getLogger(f"Plugin.{plugin_id}")
    
    def _get_logger(self) -> logging.Logger:
        if not self._logger:
            return logging.getLogger("Plugin.Unknown")
        return self._logger
    
    def debug(self, msg: str, *args, **kwargs):
        """调试日志"""
        self._get_logger().debug(msg, *args, **kwargs)
    
    def info(self, msg: str, *args, **kwargs):
        """信息日志"""
        self._get_logger().info(msg, *args, **kwargs)
    
    def warning(self, msg: str, *args, **kwargs):
        """警告日志"""
        self._get_logger().warning(msg, *args, **kwargs)
    
    def error(self, msg: str, *args, **kwargs):
        """错误日志"""
        self._get_logger().error(msg, *args, **kwargs)
    
    def critical(self, msg: str, *args, **kwargs):
        """严重错误日志"""
        self._get_logger().critical(msg, *args, **kwargs)
