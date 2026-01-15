
import json
import os
import shutil
from pathlib import Path
from typing import Dict, Any, Optional

class SoulPersistence:
    """
    璐熻矗 SoulManager 鐨勫簳灞傛枃浠?I/O 鎿嶄綔銆?
    鍘熷垯锛?
    1. 鍞竴鐨?IO 鍏ュ彛
    2. 澶勭悊 Path Traversal 瀹夊叏妫€鏌?
    3. 澶勭悊 Atomic Write (tmp -> target)
    4. 澶勭悊 JSON 搴忓垪鍖?
    """
    def __init__(self, base_dir: Path):
        self.base_dir = base_dir
        self.config_path = base_dir / "config.json"
        
    def _resolve_data_root(self) -> Path:
        """Returns characters/{id}/data/"""
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
        except Exception as e:
            print(f"[SoulPersistence] Error loading config: {e}")
            return {}

    def save_config(self, data: Dict[str, Any]):
        """Save character config (Atomic)"""
        try:
            temp_path = self.config_path.with_suffix('.tmp')
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
                # os.fsync(f.fileno()) # Optimized: Removed aggressive fsync
            
            os.replace(temp_path, self.config_path)
        except Exception as e:
            print(f"[SoulPersistence] Error saving config: {e}")

    def load_module_data(self, module_name: str) -> Dict[str, Any]:
        """Load generic module data"""
        safe_name = self._sanitize_name(module_name)
        path = self._resolve_data_root() / f"{safe_name}.json"
        
        if not path.exists():
            return {}
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            print(f"[SoulPersistence] Error loading {module_name}: {e}")
            return {}

    def save_module_data(self, module_name: str, data: Dict[str, Any]):
        """Save generic module data (Atomic)"""
        if not data: return # Optimization: Don't save empty dicts if avoidable?
        
        safe_name = self._sanitize_name(module_name)
        target_path = self._resolve_data_root() / f"{safe_name}.json"
        temp_path = self._resolve_data_root() / f"{safe_name}.tmp"
        
        try:
            with open(temp_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
                f.flush()
            
            os.replace(temp_path, target_path)
        except Exception as e:
            print(f"[SoulPersistence] Error saving {module_name}: {e}")
            if temp_path.exists():
                try: os.remove(temp_path)
                except: pass
