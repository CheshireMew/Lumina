import logging
from pathlib import Path
from typing import Any

from app_config import BASE_DIR, DATA_ROOT
from core.security.safe_path import SafePath, SecurityException
from schemas.character import CharacterConfig
from services.assets import (
    absolute_asset_url,
    cubism_core_route,
    list_live2d_models,
    live2d_renderer_route,
    live2d_model_route,
)
from services.repositories.character_file_store import CharacterFileStore

logger = logging.getLogger("CharacterService")


class CharacterService:
    """Single filesystem boundary for character configs and assets."""

    def __init__(
        self,
        *,
        soul_service: Any,
        characters_root: Path | None = None,
        seed_characters_root: Path | None = None,
    ):
        if soul_service is None:
            raise ValueError("CharacterService requires SoulService")

        self.characters_root = Path(characters_root or DATA_ROOT / "characters")
        self.seed_characters_root = Path(seed_characters_root or BASE_DIR / "characters")
        self.soul_service = soul_service

    def _active_character_id(self) -> str:
        character_id = str(self.soul_service.get_active_character_id() or "").strip()
        if not character_id:
            raise ValueError("Active companion character_id is not configured")
        return character_id

    def _character_dir(self, root: Path | None = None) -> Path:
        try:
            return SafePath.resolve_child(root or self.characters_root, self._active_character_id())
        except SecurityException as exc:
            raise ValueError("Invalid character ID") from exc

    def _config_path(self) -> Path:
        return self._character_dir() / "config.json"

    def _read_config_path(self) -> Path:
        mutable_path = self._config_path()
        if mutable_path.exists():
            return mutable_path
        return self._character_dir(self.seed_characters_root) / "config.json"

    def _read_storage_config(self, config_path: Path) -> dict[str, Any]:
        seed_path = None
        if config_path == self._config_path():
            seed_path = self._character_dir(self.seed_characters_root) / "config.json"
        return CharacterFileStore(config_path, seed_path).load()

    def _write_storage_config(self, config_path: Path, payload: dict[str, Any]) -> None:
        CharacterFileStore(
            config_path,
            self._character_dir(self.seed_characters_root) / "config.json",
        ).update(lambda current: {**current, **payload})

    def load_config(self, base_url: str | None = None) -> CharacterConfig:
        character_id = self._active_character_id()
        config_path = self._read_config_path()
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found for {character_id}")
        storage = self._read_storage_config(config_path)
        config = CharacterConfig.from_storage(character_id, storage)
        return self._with_asset_urls(config, base_url)

    def save_config(self, config: CharacterConfig) -> CharacterConfig:
        character_id = self._active_character_id()
        char_dir = self._character_dir()
        char_dir.mkdir(parents=True, exist_ok=True)

        current_storage: dict[str, Any] = {}
        read_path = self._read_config_path()
        if read_path.exists():
            current_storage = self._read_storage_config(read_path)

        current = CharacterConfig.from_storage(character_id, current_storage) if current_storage else None
        normalized = config.model_copy(update={
            "id": character_id,
            "metadata": config.metadata or (current.metadata if current else {}),
        })
        payload = normalized.to_storage()

        self._write_storage_config(self._config_path(), payload)
        return normalized

    def list_live2d_models(self) -> list[dict[str, Any]]:
        return sorted(list_live2d_models(), key=lambda item: item["name"])

    def _with_asset_urls(
        self,
        config: CharacterConfig,
        base_url: str | None,
    ) -> CharacterConfig:
        if config.avatar.type != "live2d" or not base_url:
            return config

        avatar = config.avatar.model_copy(update={
            "modelUrl": absolute_asset_url(base_url, live2d_model_route(config.avatar.model)),
            "cubismCoreUrl": absolute_asset_url(base_url, cubism_core_route()),
            "rendererRuntimeUrl": absolute_asset_url(base_url, live2d_renderer_route()),
        })
        return config.model_copy(update={"avatar": avatar})
