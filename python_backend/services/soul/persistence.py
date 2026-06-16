
import json
import os
import logging
from pathlib import Path
from typing import Dict, Any
from services.error_monitor import track_error

logger = logging.getLogger("SoulPersistence")

class SoulPersistence:
    """
    负责 SoulManager 的底层文件 I/O 操作。
    原则：
    1. 唯一的 IO 入口
    2. 处理 Path Traversal 安全检查
    3. 处理 Atomic Write (tmp -> target)
    4. 处理 JSON 序列化
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = base_dir / "config.json"
        
    def _resolve_data_root(self) -> Path:
        """Returns the active character data directory."""
        path = self.base_dir / "data"
        path.mkdir(parents=True, exist_ok=True)
        return path

    def _sanitize_name(self, name: str) -> str:
        """Prevent path traversal"""
        return Path(name).name

    def load_config(self) -> Dict[str, Any]:
        """Load character config"""
        if not self.config_path.exists():
            return {}
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in config: {e}")
            track_error(e, context={"file": str(self.config_path)})
            return {}
        except Exception as e:
            logger.error(f"Error loading config: {e}")
            track_error(e, context={"file": str(self.config_path)})
            return {}

    def save_config(self, data: Dict[str, Any]):
        """Save character config (Atomic)"""
        try:
            temp_path = self.config_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            os.replace(temp_path, self.config_path)
            logger.debug(f"Config saved: {self.config_path}")
        except Exception as e:
            logger.error(f"Error saving config: {e}")
            track_error(e, context={"file": str(self.config_path)})
            # Clean up temp file if exists
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

    def load_module_data(self, module_name: str) -> Dict[str, Any]:
        """Load generic module data"""
        safe_name = self._sanitize_name(module_name)
        path = self._resolve_data_root() / f"{safe_name}.json"
        
        if not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except json.JSONDecodeError as e:
            logger.error(f"Invalid JSON in {module_name}: {e}")
            track_error(e, context={"module": module_name, "file": str(path)})
            return {}
        except Exception as e:
            logger.error(f"Error loading {module_name}: {e}")
            track_error(e, context={"module": module_name, "file": str(path)})
            return {}

    def save_module_data(self, module_name: str, data: Dict[str, Any]):
        """Save generic module data (Atomic)"""
        if not data:
            return  # Optimization: Don't save empty dicts
        
        safe_name = self._sanitize_name(module_name)
        target_path = self._resolve_data_root() / f"{safe_name}.json"
        temp_path = self._resolve_data_root() / f"{safe_name}.tmp"
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            os.replace(temp_path, target_path)
            logger.debug(f"Module data saved: {module_name}")
        except Exception as e:
            logger.error(f"Error saving {module_name}: {e}")
            track_error(e, context={"module": module_name, "file": str(target_path)})
            if temp_path.exists():
                try:
                    os.remove(temp_path)
                except OSError:
                    pass

