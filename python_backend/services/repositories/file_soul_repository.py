from pathlib import Path
from typing import Any, Dict, Optional

from app_config import BASE_DIR
from core.interfaces.repository import ISoulRepository
from services.soul.persistence import SoulPersistence


class FileSoulRepository(ISoulRepository):
    def __init__(self, character_id: str, characters_root: Optional[Path] = None):
        self.characters_root = Path(characters_root or BASE_DIR / "characters")
        self.character_id = self._normalize_character_id(character_id)
        self._persistence = self._build_persistence(self.character_id)

    def _normalize_character_id(self, character_id: str) -> str:
        normalized = Path(str(character_id or "").strip()).name
        if not normalized:
            raise ValueError("character_id must be configured")
        return normalized

    def _build_persistence(self, character_id: str) -> SoulPersistence:
        character_dir = self.characters_root / character_id
        character_dir.mkdir(parents=True, exist_ok=True)
        return SoulPersistence(character_dir)

    def get_character_id(self) -> str:
        return self.character_id

    def load_config(self) -> Dict[str, Any]:
        return self._persistence.load_config()

    def save_config(self, data: Dict[str, Any]):
        self._persistence.save_config(data)

    def load_module_data(self, module_id: str) -> Dict[str, Any]:
        return self._persistence.load_module_data(module_id)

    def save_module_data(self, module_id: str, data: Dict[str, Any]):
        self._persistence.save_module_data(module_id, data)

    def get_data_dir(self, module_id: str = None) -> Path:
        if module_id:
            return self._persistence._resolve_data_root() / Path(module_id).name
        return self._persistence._resolve_data_root()
