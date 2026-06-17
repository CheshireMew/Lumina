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
