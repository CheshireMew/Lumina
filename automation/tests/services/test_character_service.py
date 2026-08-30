import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.character_service import CharacterService


class FakeSoulService:
    def __init__(self, character_id: str = "sakura"):
        self.character_id = character_id

    def get_active_character_id(self) -> str:
        return self.character_id


def test_character_service_requires_soul_service_for_active_character():
    with pytest.raises(ValueError, match="requires SoulService"):
        CharacterService(
            characters_root=Path("characters"),
            soul_service=None,
        )


def test_character_service_rejects_empty_active_character():
    service = CharacterService(
        characters_root=Path("characters"),
        soul_service=FakeSoulService(""),
    )

    with pytest.raises(ValueError, match="Active companion character_id is not configured"):
        service.load_config()


def test_character_service_loads_config_for_active_companion(tmp_path: Path):
    char_dir = tmp_path / "characters" / "sakura"
    char_dir.mkdir(parents=True)
    (char_dir / "config.json").write_text(
        '{"name": "Sakura", "description": "Configured character"}',
        encoding="utf-8",
    )
    service = CharacterService(
        characters_root=tmp_path / "characters",
        soul_service=FakeSoulService("sakura"),
    )

    config = service.load_config()

    assert config.id == "sakura"
    assert config.name == "Sakura"


def test_character_service_reads_seed_and_writes_mutable_override(tmp_path: Path):
    seed_root = tmp_path / "seed"
    mutable_root = tmp_path / "mutable"
    seed_dir = seed_root / "sakura"
    seed_dir.mkdir(parents=True)
    (seed_dir / "config.json").write_text(
        '{"name": "Sakura", "description": "Seed description"}',
        encoding="utf-8",
    )
    service = CharacterService(
        characters_root=mutable_root,
        seed_characters_root=seed_root,
        soul_service=FakeSoulService("sakura"),
    )

    seeded = service.load_config()
    service.save_config(seeded.model_copy(update={"description": "User description"}))

    assert seeded.description == "Seed description"
    assert service.load_config().description == "User description"
    assert "Seed description" in (seed_dir / "config.json").read_text(encoding="utf-8")
    assert (mutable_root / "sakura" / "config.json").exists()


def test_character_service_persists_live2d_behavior_as_character_data(tmp_path: Path):
    char_dir = tmp_path / "characters" / "sakura"
    char_dir.mkdir(parents=True)
    (char_dir / "config.json").write_text(
        '{"name": "Sakura", "avatar": {"model": "Sakura", '
        '"behavior": {"idleMotionGroup": "Breathing", "tapHitArea": "Head"}}}',
        encoding="utf-8",
    )
    service = CharacterService(
        characters_root=tmp_path / "characters",
        soul_service=FakeSoulService("sakura"),
    )

    config = service.load_config()
    assert config.avatar.behavior.idleMotionGroup == "Breathing"
    assert config.avatar.behavior.tapHitArea == "Head"

    service.save_config(config)
    assert service.load_config().avatar.behavior.idleMotionGroup == "Breathing"
