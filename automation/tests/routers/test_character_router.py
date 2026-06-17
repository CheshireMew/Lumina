import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from routers.character import get_character_config
from schemas.character import CharacterConfig


class MissingCharacterService:
    def load_config(self):
        raise FileNotFoundError("missing active companion")


class FakeCharacterService:
    def load_config(self):
        return CharacterConfig(id="sakura", name="Sakura", displayName="Sakura")


@pytest.mark.anyio
async def test_get_character_config_returns_active_companion():
    config = await get_character_config(character_service=FakeCharacterService())

    assert config.id == "sakura"


@pytest.mark.anyio
async def test_get_character_config_does_not_fallback_to_hiyori():
    with pytest.raises(HTTPException) as exc_info:
        await get_character_config(character_service=MissingCharacterService())

    assert exc_info.value.status_code == 404
    assert "missing active companion" in exc_info.value.detail
