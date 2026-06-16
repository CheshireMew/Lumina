from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from services.orchestrators.soul import SOUL_DRIVER_CONFIG_KEY, SoulService
from services.repositories.file_soul_repository import FileSoulRepository

pytestmark = pytest.mark.anyio


class InMemorySoulRepository:
    def __init__(self, character_id: str = "hiyori"):
        self.character_id = character_id
        self.config = {"name": "Hiyori", "description": "AI companion", "system_prompt": ""}
        self.modules: dict[str, dict] = {}

    def set_character_id(self, character_id: str):
        self.character_id = character_id

    def get_character_id(self) -> str:
        return self.character_id

    def load_config(self) -> dict:
        return dict(self.config)

    def save_config(self, data: dict):
        self.config = dict(data)

    def load_module_data(self, module_id: str) -> dict:
        return dict(self.modules.get(module_id, {}))

    def save_module_data(self, module_id: str, data: dict):
        self.modules[module_id] = dict(data)

    def get_data_dir(self, module_id: str = None) -> Path:
        return Path("data") / (module_id or "")


def build_driver(driver_id: str = "test.soul", prompt: str = "You are a test assistant."):
    driver = SimpleNamespace(
        id=driver_id,
        metadata={"name": "Test Soul"},
        get_system_prompt=AsyncMock(return_value=prompt),
        on_interaction=AsyncMock(),
        get_state=MagicMock(return_value={"mood": "happy", "energy": 80}),
    )
    return driver


async def test_soul_service_initialization_uses_repository_character():
    repo = InMemorySoulRepository("hiyori")
    service = SoulService(repo=repo)

    await service.initialize()

    assert service.get_active_character_id() == "hiyori"
    assert service._active_driver is None


async def test_system_config_sets_repository_character():
    repo = InMemorySoulRepository()
    config = SimpleNamespace(memory=SimpleNamespace(character_id="sakura"))

    service = SoulService(system_config=config, repo=repo)

    assert service.get_active_character_id() == "sakura"


async def test_soul_service_requires_config_or_repository():
    with pytest.raises(ValueError, match="requires system_config or repo"):
        SoulService()


async def test_register_driver_does_not_activate_unselected_driver():
    service = SoulService(repo=InMemorySoulRepository())
    driver = build_driver()

    service.register_driver(driver)

    assert service._drivers["test.soul"] is driver
    assert service._active_driver is None


async def test_register_driver_restores_character_selected_driver():
    repo = InMemorySoulRepository()
    repo.config[SOUL_DRIVER_CONFIG_KEY] = "test.soul"
    service = SoulService(repo=repo)
    driver = build_driver()

    service.register_driver(driver)

    assert service._active_driver is driver


async def test_set_active_driver_switches_known_driver_and_persists_selection():
    service = SoulService(repo=InMemorySoulRepository())
    driver1 = build_driver("soul1")
    driver2 = build_driver("soul2")
    service._drivers = {"soul1": driver1, "soul2": driver2}
    service._active_driver = driver1

    service.set_active_driver("soul2")

    assert service._active_driver is driver2
    assert service.load_character_config()[SOUL_DRIVER_CONFIG_KEY] == "soul2"


async def test_set_active_driver_rejects_unknown_driver():
    service = SoulService(repo=InMemorySoulRepository())

    with pytest.raises(ValueError, match="Unknown Soul driver"):
        service.set_active_driver("missing.soul")


async def test_get_system_prompt_uses_active_driver():
    service = SoulService(repo=InMemorySoulRepository())
    driver = build_driver(prompt="Driver prompt")
    service._active_driver = driver

    prompt = await service.get_system_prompt({"topic": "test"})

    assert prompt == "Driver prompt"
    driver.get_system_prompt.assert_awaited_once_with({"topic": "test"})


async def test_get_system_prompt_renders_template_from_repository_config(tmp_path: Path):
    repo = InMemorySoulRepository()
    repo.config = {
        "name": "TestChar",
        "description": "A test character",
        "system_prompt": "Custom instructions",
    }
    service = SoulService(repo=repo)
    template_path = tmp_path / "prompts" / "chat" / "system.yaml"
    template_path.parent.mkdir(parents=True)
    template_path.write_text("line: |\n  {{ char_name }} {{ custom_prompt }}", encoding="utf-8")

    with patch("app_config.BASE_DIR", tmp_path):
        prompt = await service.get_system_prompt()

    assert prompt == "TestChar Custom instructions"


async def test_on_interaction_delegates_to_active_driver():
    service = SoulService(repo=InMemorySoulRepository())
    driver = build_driver()
    service._active_driver = driver

    await service.on_interaction("Hello", "Hi", {"context": "test"})

    driver.on_interaction.assert_awaited_once_with("Hello", "Hi", {"context": "test"})


async def test_profile_combines_driver_state_and_runtime_state():
    repo = InMemorySoulRepository()
    repo.modules["soul.runtime"] = {"last_interaction_at": 123}
    service = SoulService(repo=repo)
    service._active_driver = build_driver()

    assert service.profile == {"mood": "happy", "energy": 80, "last_interaction_at": 123}


async def test_repository_delegates_character_and_module_data():
    repo = InMemorySoulRepository()
    service = SoulService(repo=repo)

    service.save_character_config({"name": "UpdatedChar"})
    service.save_module_data("test_module", {"key": "value"})

    assert service.load_character_config() == {"name": "UpdatedChar"}
    assert service.load_module_data("test_module") == {"key": "value"}


async def test_file_soul_repository_persists_config_and_module_data(tmp_path: Path):
    repo = FileSoulRepository(characters_root=tmp_path / "characters", character_id="hiyori")

    repo.save_config({"name": "Hiyori"})
    repo.save_module_data("runtime", {"mood": "calm"})

    assert repo.load_config() == {"name": "Hiyori"}
    assert repo.load_module_data("runtime") == {"mood": "calm"}
    assert repo.get_data_dir("runtime").name == "runtime"


async def test_file_soul_repository_requires_character_id(tmp_path: Path):
    with pytest.raises(ValueError, match="character_id must be configured"):
        FileSoulRepository(characters_root=tmp_path / "characters", character_id="")
