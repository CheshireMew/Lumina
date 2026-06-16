from pathlib import Path

import pytest

from services.orchestrators.soul import SoulService
from services.repositories.file_soul_repository import FileSoulRepository

pytestmark = pytest.mark.anyio


async def test_soul_service_uses_file_repository(tmp_path: Path):
    repo = FileSoulRepository(characters_root=tmp_path / "characters", character_id="hiyori")
    repo.save_config({"name": "Hiyori", "description": "AI companion"})

    service = SoulService(repo=repo)

    assert service.get_active_character_id() == "hiyori"
    assert service.load_character_config()["name"] == "Hiyori"


async def test_soul_runtime_state_persistence(tmp_path: Path):
    repo = FileSoulRepository(characters_root=tmp_path / "characters", character_id="hiyori")
    service = SoulService(repo=repo)

    service.save_module_data("soul.runtime", {"test": "data"})

    assert service.load_module_data("soul.runtime") == {"test": "data"}
