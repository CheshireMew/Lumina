"""
Storage 模块
============

插件专属持久化存储。

Example:
    await lumina.storage.set("key", {"data": 123})
    value = await lumina.storage.get("key")
"""

import json
import logging
from pathlib import Path
from typing import Any, Optional, List

logger = logging.getLogger("Lumina.SDK.Storage")


class StorageModule:
    """
    持久化存储模块
    
    每个插件有独立的存储空间，数据自动隔离。
    
    Methods:
        set(key, value) - 存储数据
        get(key, default) - 获取数据
        delete(key) - 删除数据
        keys() - 列出所有 Key
    """
    
    def __init__(self, container):
        self._container = container
        self._plugin_id: Optional[str] = None
        self._storage_dir: Optional[Path] = None
    
    def _set_plugin_context(self, plugin_id: str):
        """由系统调用，设置插件上下文"""
        self._plugin_id = plugin_id
        
        # 获取数据目录
        from app_config import config
        data_dir = Path(config.paths.data_dir) / "plugins" / plugin_id
        data_dir.mkdir(parents=True, exist_ok=True)
        self._storage_dir = data_dir
    
    def _get_storage_path(self) -> Path:
        """获取存储文件路径"""
        if not self._storage_dir:
            raise RuntimeError("Storage 未初始化，请在 load(context) 之后使用")
        return self._storage_dir / "storage.json"
    
    def _load_data(self) -> dict:
        """加载存储数据"""
        path = self._get_storage_path()
        if path.exists():
            try:
                return json.loads(path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.warning(f"Failed to load storage: {e}")
        return {}
    
    def _save_data(self, data: dict):
        """保存存储数据"""
        path = self._get_storage_path()
        path.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
    
    async def set(self, key: str, value: Any) -> None:
        """
        存储数据
        
        Args:
            key: 键名
            value: 值（必须可 JSON 序列化）
        
        Example:
            await lumina.storage.set("user_prefs", {"theme": "dark"})
        """
        data = self._load_data()
        data[key] = value
        self._save_data(data)
    
    async def get(self, key: str, default: Any = None) -> Any:
        """
        获取数据
        
        Args:
            key: 键名
            default: 默认值
        
        Returns:
            存储的值，不存在则返回 default
        
        Example:
            prefs = await lumina.storage.get("user_prefs", {})
        """
        data = self._load_data()
        return data.get(key, default)
    
    async def delete(self, key: str) -> bool:
        """
        删除数据
        
        Args:
            key: 键名
        
        Returns:
            是否删除成功
        """
        data = self._load_data()
        if key in data:
            del data[key]
            self._save_data(data)
            return True
        return False
    
    async def keys(self) -> List[str]:
        """
        列出所有 Key
        
        Returns:
            所有键名列表
        """
        data = self._load_data()
        return list(data.keys())
    
    async def clear(self) -> None:
        """清空所有数据"""
        self._save_data({})
