import sys
from pathlib import Path
from types import SimpleNamespace

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.character_service import CharacterService


def test_character_service_requires_system_config_for_active_character():
    service = CharacterService(characters_root=Path("characters"))

    with pytest.raises(ValueError, match="requires system_config"):
        service.load_config()


def test_character_service_rejects_empty_configured_character():
    service = CharacterService(
        characters_root=Path("characters"),
        system_config=SimpleNamespace(memory=SimpleNamespace(character_id="")),
    )

    with pytest.raises(ValueError, match="memory.character_id must be configured"):
        service.load_config()


def test_character_service_loads_config_for_configured_character(tmp_path: Path):
    char_dir = tmp_path / "characters" / "sakura"
    char_dir.mkdir(parents=True)
    (char_dir / "config.json").write_text(
        '{"name": "Sakura", "description": "Configured character"}',
        encoding="utf-8",
    )
    service = CharacterService(
        characters_root=tmp_path / "characters",
        system_config=SimpleNamespace(memory=SimpleNamespace(character_id="sakura")),
    )

    config = service.load_config()

    assert config.id == "sakura"
    assert config.name == "Sakura"
