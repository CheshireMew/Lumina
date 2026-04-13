import json
import logging
import shutil
from pathlib import Path
from typing import Any

from app_config import BASE_DIR
from core.security.safe_path import SafePath, SecurityException
from schemas.character import CharacterConfig

logger = logging.getLogger("CharacterService")


class CharacterService:
    """Single filesystem boundary for character configs and assets."""

    def __init__(self, characters_root: Path | None = None):
        self.characters_root = characters_root or (BASE_DIR / "characters")

    def _character_dir(self, character_id: str) -> Path:
        try:
            return SafePath.resolve_child(self.characters_root, character_id)
        except SecurityException as exc:
            raise ValueError("Invalid character ID") from exc

    def _config_path(self, character_id: str) -> Path:
        return self._character_dir(character_id) / "config.json"

    def list_characters(self) -> list[CharacterConfig]:
        characters: list[CharacterConfig] = []
        if not self.characters_root.exists():
            return characters

        for char_dir in self.characters_root.iterdir():
            if not char_dir.is_dir():
                continue
            config_path = char_dir / "config.json"
            if not config_path.exists():
                continue
            try:
                with open(config_path, "r", encoding="utf-8") as handle:
                    config = json.load(handle)
                characters.append(CharacterConfig.from_storage(char_dir.name, config))
            except Exception as exc:
                logger.error("Failed to load character config for %s: %s", char_dir.name, exc)
        return characters

    def load_config(self, character_id: str) -> CharacterConfig:
        config_path = self._config_path(character_id)
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found for {character_id}")
        with open(config_path, "r", encoding="utf-8") as handle:
            config = json.load(handle)
        return CharacterConfig.from_storage(character_id, config)

    def save_config(self, character_id: str, config: CharacterConfig) -> CharacterConfig:
        char_dir = self._character_dir(character_id)
        char_dir.mkdir(parents=True, exist_ok=True)

        current_storage: dict[str, Any] = {}
        config_path = self._config_path(character_id)
        if config_path.exists():
            with open(config_path, "r", encoding="utf-8") as handle:
                current_storage = json.load(handle)

        current = CharacterConfig.from_storage(character_id, current_storage) if current_storage else None
        normalized = config.model_copy(update={
            "id": character_id,
            "metadata": config.metadata or (current.metadata if current else {}),
        })
        payload = normalized.to_storage()

        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
            handle.flush()
        temp_path.replace(config_path)
        return normalized

    def delete_character(self, character_id: str) -> bool:
        if character_id == "hiyori":
            raise ValueError("Cannot delete default character 'hiyori'")

        char_dir = self._character_dir(character_id)
        if not char_dir.exists():
            return False
        if not char_dir.is_dir():
            raise ValueError("Character path is not a directory")
        shutil.rmtree(char_dir)
        return True

    def list_live2d_models(self, system_plugin_manager: Any = None) -> list[dict[str, Any]]:
        if system_plugin_manager:
            plugin = system_plugin_manager.get_plugin("system.avatar_server")
            if plugin and hasattr(plugin, "scan_models"):
                return plugin.scan_models()
        return []
