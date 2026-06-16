import json
import logging
from pathlib import Path
from typing import Any

from app_config import BASE_DIR
from core.security.safe_path import SafePath, SecurityException
from schemas.character import CharacterConfig

logger = logging.getLogger("CharacterService")


class CharacterService:
    """Single filesystem boundary for character configs and assets."""

    def __init__(
        self,
        characters_root: Path | None = None,
        package_registry: Any | None = None,
        system_config: Any | None = None,
    ):
        self.characters_root = characters_root or (BASE_DIR / "characters")
        self.package_registry = package_registry
        self.system_config = system_config

    def _active_character_id(self) -> str:
        if self.system_config is None:
            raise ValueError("CharacterService requires system_config")
        character_id = str(self.system_config.memory.character_id or "").strip()
        if not character_id:
            raise ValueError("memory.character_id must be configured")
        return character_id

    def _character_dir(self) -> Path:
        try:
            return SafePath.resolve_child(self.characters_root, self._active_character_id())
        except SecurityException as exc:
            raise ValueError("Invalid character ID") from exc

    def _config_path(self) -> Path:
        return self._character_dir() / "config.json"

    def _read_storage_config(self, config_path: Path) -> dict[str, Any]:
        with open(config_path, "r", encoding="utf-8") as handle:
            return json.load(handle)

    def _write_storage_config(self, config_path: Path, payload: dict[str, Any]) -> None:
        temp_path = config_path.with_suffix(".tmp")
        with open(temp_path, "w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=4, ensure_ascii=False)
            handle.flush()
        temp_path.replace(config_path)

    def _get_live2d_snapshot(self) -> Any | None:
        if not self.package_registry:
            return None

        snapshot = self.package_registry.resolve("live2d-assets")
        if not snapshot or snapshot.status != "ready":
            return None
        return snapshot

    def load_config(self) -> CharacterConfig:
        character_id = self._active_character_id()
        config_path = self._config_path()
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found for {character_id}")
        storage = self._read_storage_config(config_path)
        return CharacterConfig.from_storage(character_id, storage)

    def save_config(self, config: CharacterConfig) -> CharacterConfig:
        character_id = self._active_character_id()
        char_dir = self._character_dir()
        char_dir.mkdir(parents=True, exist_ok=True)

        current_storage: dict[str, Any] = {}
        config_path = self._config_path()
        if config_path.exists():
            current_storage = self._read_storage_config(config_path)

        current = CharacterConfig.from_storage(character_id, current_storage) if current_storage else None
        normalized = config.model_copy(update={
            "id": character_id,
            "metadata": config.metadata or (current.metadata if current else {}),
        })
        payload = normalized.to_storage()

        self._write_storage_config(config_path, payload)
        return normalized

    def list_live2d_models(self, system_plugin_manager: Any = None) -> list[dict[str, Any]]:
        _ = system_plugin_manager
        models: list[dict[str, Any]] = []
        models.extend(self._scan_live2d_models())
        return sorted(models, key=lambda item: item["name"])

    def _scan_live2d_models(self) -> list[dict[str, Any]]:
        snapshot = self._get_live2d_snapshot()
        if not snapshot:
            return []

        live2d_root = snapshot.resource_dirs.get("live2d")
        if not live2d_root or not live2d_root.exists():
            return []

        models: list[dict[str, Any]] = []
        seen_names: set[str] = set()
        for model_path in live2d_root.rglob("*.model3.json"):
            name = model_path.parent.name if model_path.parent.name != "imported" else model_path.stem
            if name in seen_names:
                continue
            seen_names.add(name)
            rel_path = model_path.relative_to(live2d_root).as_posix()
            models.append(
                {
                    "name": name,
                    "path": snapshot.resource_route("live2d", rel_path),
                    "type": "live2d",
                    "thumbnail": self._resolve_live2d_thumbnail(snapshot, model_path, live2d_root),
                    "availability": "ready",
                }
            )
        return models

    def _resolve_live2d_thumbnail(self, snapshot: Any, asset_path: Path, root: Path) -> str | None:
        for candidate in (
            "thumbnail.png",
            "thumbnail.jpg",
            "preview.png",
            "preview.jpg",
            f"{asset_path.stem}.png",
            f"{asset_path.stem}.jpg",
            "icon.png",
        ):
            thumb_path = asset_path.parent / candidate
            if thumb_path.exists():
                relative = thumb_path.relative_to(root).as_posix()
                return snapshot.resource_route("live2d", relative)
        return None
