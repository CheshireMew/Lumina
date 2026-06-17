import sys
from pathlib import Path
from typing import AsyncGenerator
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.interfaces.driver import BaseTTSDriver
from services.managers.tts import TTSPluginManager


class ConfigStub:
    def __init__(self, selected_provider=None):
        self.selected_provider = selected_provider

    def get_selected_provider(self, _capability):
        return self.selected_provider

    def is_provider_desired_enabled(self, _provider_id):
        return True

    def get_provider_settings(self, _provider_id):
        return {}


class FakeTTSDriver(BaseTTSDriver):
    def __init__(self, driver_id="test.tts.driver"):
        super().__init__(driver_id, "Test TTS Driver")
        self.loaded = False
        self.unloaded = False

    async def load(self):
        self.loaded = True

    async def unload(self):
        self.unloaded = True

    async def list_voices(self):
        return [{"name": "voice-a", "gender": "Unknown", "locale": "zh-CN"}]

    async def generate_stream(
        self,
        text: str,
        voice: str,
        **kwargs,
    ) -> AsyncGenerator[bytes, None]:
        yield f"{voice}:{text}".encode()


def make_manager(selected_provider=None) -> TTSPluginManager:
    return TTSPluginManager(ConfigStub(selected_provider=selected_provider))


def test_tts_manager_initialization():
    manager = make_manager()

    assert manager.iter_drivers() == ()
    assert manager.active_driver_id == "none"
    assert manager.loading_status == "idle"


@pytest.mark.anyio
async def test_tts_activation_loads_driver():
    manager = make_manager()
    driver = FakeTTSDriver()
    manager.register_driver(driver)

    await manager.activate(driver.id)

    assert manager.active_driver is driver
    assert manager.active_driver_id == driver.id
    assert driver.loaded is True


@pytest.mark.anyio
async def test_tts_activate_requires_known_driver():
    manager = make_manager()
    driver = FakeTTSDriver()
    manager.register_driver(driver)

    with pytest.raises(ValueError, match="Unknown TTS provider"):
        await manager.activate("missing.driver")


@pytest.mark.anyio
async def test_tts_no_drivers_enters_degraded_mode():
    manager = make_manager()

    await manager.activate("missing.driver")

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"


@pytest.mark.anyio
async def test_tts_unload_active_driver_uses_contract():
    manager = make_manager()
    driver = FakeTTSDriver()
    manager.register_driver(driver)
    await manager.activate(driver.id)

    await manager.unload_active_driver()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert driver.unloaded is True


@pytest.mark.anyio
async def test_tts_driver_voice_contract():
    driver = FakeTTSDriver()

    assert await driver.list_voices() == [
        {"name": "voice-a", "gender": "Unknown", "locale": "zh-CN"}
    ]


def test_tts_driver_config_updates_use_provider_host_boundary():
    manager = make_manager()
    driver = FakeTTSDriver()
    manager.register_driver(driver)

    config = manager.update_driver_config(driver.id, "voice", "voice-a")

    assert config["voice"] == "voice-a"
    assert driver.config["voice"] == "voice-a"


def test_tts_resolve_driver_supports_direct_and_prefixed_ids():
    manager = make_manager()
    driver = FakeTTSDriver("driver.tts.edge")
    manager.register_driver(driver)

    assert manager.resolve_driver("driver.tts.edge") is driver
    assert manager.resolve_driver("edge") is driver


@pytest.mark.anyio
async def test_tts_startup_requires_selected_provider():
    manager = make_manager()
    driver = FakeTTSDriver("driver.tts.edge")

    with patch(
        "services.managers.driver_loader.DriverLoader.load_plugins",
        return_value=[driver],
    ):
        await manager.register_drivers()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert manager.last_error == "No TTS provider selected in configuration"


@pytest.mark.anyio
async def test_tts_startup_rejects_missing_selected_provider():
    manager = make_manager(selected_provider="driver.tts.edge")
    driver = FakeTTSDriver("driver.tts.other")

    with patch(
        "services.managers.driver_loader.DriverLoader.load_plugins",
        return_value=[driver],
    ):
        await manager.register_drivers()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert manager.last_error == "Configured TTS provider not discovered: driver.tts.edge"
