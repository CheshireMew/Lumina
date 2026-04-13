"""
Config 模块
===========

插件配置读写功能。

Example:
    api_key = await lumina.config.get("api_key")
    await lumina.config.set("api_key", "sk-xxx")
"""

import logging
from typing import Any, Optional, Dict

logger = logging.getLogger("Lumina.SDK.Config")


class ConfigModule:
    """
    配置模块
    
    每个插件有独立的配置空间，数据自动隔离。
    
    Methods:
        get(key, default) - 获取配置
        set(key, value) - 设置配置
        get_all() - 获取所有配置
    """
    
    def __init__(self, container):
        self._container = container
        self._plugin_id: Optional[str] = None
    
    def _set_plugin_context(self, plugin_id: str):
        """由系统调用，设置插件上下文"""
        self._plugin_id = plugin_id
    
    def _get_plugin_config(self) -> Dict[str, Any]:
        """获取插件配置字典"""
        if not self._plugin_id:
            return {}
        
        # [Refactor] Use Injected Config
        # This assumes ConfigManager implements IConfigProvider
        config = self._container.config
        if not config:
            logger.warning("Config provider not found in container")
            return {}
            
        # Access plugins directly (ConfigManager.get() or .plugins property)
        # Using .plugins property for now as it's cleaner
        try:
             settings = getattr(config.plugins, 'settings', {})
             if isinstance(settings, dict):
                return settings.get(self._plugin_id, {})
        except Exception as e:
             logger.error(f"Failed to access config: {e}")
             
        return {}
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取配置值
        
        Args:
            key: 配置键名
            default: 默认值
        
        Returns:
            配置值，不存在则返回 default
        
        Example:
            api_key = await lumina.config.get("api_key", "")
        """
        config_dict = self._get_plugin_config()
        return config_dict.get(key, default)
    
    async def set(self, key: str, value: Any) -> None:
        """
        设置配置值
        
        Args:
            key: 配置键名
            value: 配置值
        
        Example:
            await lumina.config.set("api_key", "sk-xxx")
        """
        if not self._plugin_id:
            raise RuntimeError("Config 未初始化，请在 load(context) 之后使用")
            
        config = self._container.config
        if not config:
             raise RuntimeError("Config provider not available")
        
        # 确保 settings 存在
        if not hasattr(config.plugins, 'settings'):
            config.plugins.settings = {}
        
        settings = config.plugins.settings
        if not isinstance(settings, dict):
            settings = {}
            config.plugins.settings = settings
        
        if self._plugin_id not in settings:
            settings[self._plugin_id] = {}
        
        settings[self._plugin_id][key] = value
        
        # 保存配置
        try:
            config.save()
        except Exception as e:
            logger.error(f"Failed to save config: {e}")
    
    async def get_all(self) -> Dict[str, Any]:
        """
        获取所有配置
        
        Returns:
            配置字典
        """
        return self._get_plugin_config()
    
    async def delete(self, key: str) -> bool:
        """
        删除配置
        
        Args:
            key: 配置键名
        
        Returns:
            是否删除成功
        """
        if not self._plugin_id:
            return False
            
        config = self._container.config
        
        settings = getattr(config.plugins, 'settings', {})
        if isinstance(settings, dict) and self._plugin_id in settings:
            plugin_config = settings[self._plugin_id]
            if key in plugin_config:
                del plugin_config[key]
                config.save()
                return True
        
        return False
    
    async def clear(self) -> None:
        """清空插件配置"""
        if not self._plugin_id:
            return
            
        config = self._container.config
        
        settings = getattr(config.plugins, 'settings', {})
        if isinstance(settings, dict) and self._plugin_id in settings:
            settings[self._plugin_id] = {}
            config.save()
