
import logging
from pathlib import Path
from typing import Dict, Any
from services.repositories.character_file_store import CharacterFileStore

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
    def __init__(self, base_dir: Path, seed_dir: Path | None = None):
        self.base_dir = Path(base_dir)
        self.seed_dir = Path(seed_dir) if seed_dir else None
        self.base_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = base_dir / "config.json"
        self._config_store = CharacterFileStore(
            self.config_path,
            (self.seed_dir / "config.json") if self.seed_dir else None,
        )

    def _read_path(self, relative_path: Path) -> Path:
        mutable_path = self.base_dir / relative_path
        if mutable_path.exists() or self.seed_dir is None:
            return mutable_path
        return self.seed_dir / relative_path
        
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
        return self._config_store.load()

    def save_config(self, data: Dict[str, Any]):
        """Save character config (Atomic)"""
        self._config_store.save(data)
        logger.debug("Config saved: %s", self.config_path)

    def update_config_fields(self, updates: Dict[str, Any]) -> Dict[str, Any]:
        return self._config_store.update(lambda current: {**current, **updates})

    def load_module_data(self, module_name: str) -> Dict[str, Any]:
        """Load generic module data"""
        safe_name = self._sanitize_name(module_name)
        mutable = self.base_dir / "data" / f"{safe_name}.json"
        seed = self.seed_dir / "data" / f"{safe_name}.json" if self.seed_dir else None
        return CharacterFileStore(mutable, seed).load()

    def save_module_data(self, module_name: str, data: Dict[str, Any]):
        """Save generic module data (Atomic)"""
        safe_name = self._sanitize_name(module_name)
        target_path = self._resolve_data_root() / f"{safe_name}.json"
        seed_path = self.seed_dir / "data" / f"{safe_name}.json" if self.seed_dir else None
        CharacterFileStore(target_path, seed_path).save(data)
        logger.debug("Module data saved: %s", module_name)

