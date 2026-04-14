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

    def __init__(self, characters_root: Path | None = None, package_registry: Any | None = None):
        self.characters_root = characters_root or (BASE_DIR / "characters")
        self.package_registry = package_registry

    def _character_dir(self, character_id: str) -> Path:
        try:
            return SafePath.resolve_child(self.characters_root, character_id)
        except SecurityException as exc:
            raise ValueError("Invalid character ID") from exc

    def _config_path(self, character_id: str) -> Path:
        return self._character_dir(character_id) / "config.json"

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
                characters.append(self.load_config(char_dir.name))
            except Exception as exc:
                logger.error("Failed to load character config for %s: %s", char_dir.name, exc)
        return characters

    def load_config(self, character_id: str) -> CharacterConfig:
        config_path = self._config_path(character_id)
        if not config_path.exists():
            raise FileNotFoundError(f"Config not found for {character_id}")
        storage = self._read_storage_config(config_path)
        return CharacterConfig.from_storage(character_id, storage)

    def save_config(self, character_id: str, config: CharacterConfig) -> CharacterConfig:
        char_dir = self._character_dir(character_id)
        char_dir.mkdir(parents=True, exist_ok=True)

        current_storage: dict[str, Any] = {}
        config_path = self._config_path(character_id)
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
        _ = system_plugin_manager
        models: list[dict[str, Any]] = []
        models.extend(self._scan_live2d_models())
        models.extend(self._scan_public_models("vrm", ".vrm"))
        models.extend(self._scan_sprite_models())
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

    def _scan_public_models(self, folder: str, suffix: str) -> list[dict[str, Any]]:
        public_root = BASE_DIR.parent / "public" / folder
        if not public_root.exists():
            return []

        models: list[dict[str, Any]] = []
        for asset_path in public_root.rglob(f"*{suffix}"):
            models.append(
                {
                    "name": asset_path.stem,
                    "path": f"/{asset_path.relative_to(BASE_DIR.parent / 'public').as_posix()}",
                    "type": folder,
                    "thumbnail": self._resolve_thumbnail(asset_path, public_root, folder),
                    "availability": "ready",
                }
            )
        return models

    def _scan_sprite_models(self) -> list[dict[str, Any]]:
        sprites_root = BASE_DIR.parent / "public" / "sprites"
        if not sprites_root.exists():
            return []

        models: list[dict[str, Any]] = []
        for entry in sprites_root.iterdir():
            if not entry.is_dir():
                continue
            for candidate in ("default.png", "normal.png", "stand.png"):
                sprite_path = entry / candidate
                if not sprite_path.exists():
                    continue
                relative = sprite_path.relative_to(BASE_DIR.parent / "public").as_posix()
                models.append(
                    {
                        "name": entry.name,
                        "path": f"/{relative}",
                        "type": "sprite",
                        "thumbnail": f"/{relative}",
                        "availability": "ready",
                    }
                )
                break
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

    def _resolve_thumbnail(self, asset_path: Path, root: Path, kind: str) -> str | None:
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
                return f"/{kind}/{thumb_path.relative_to(root).as_posix()}"
        return None
