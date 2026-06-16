import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.interfaces.driver import BaseSTTDriver
from services.managers.stt import STTPluginManager


class ConfigStub:
    def __init__(self, selected_provider=None):
        self.selected_provider = selected_provider

    def get_selected_provider(self, _capability):
        return self.selected_provider

    def is_plugin_desired_enabled(self, _plugin_id):
        return True

    def get_plugin_settings(self, _plugin_id):
        return {}


class FakeSTTDriver(BaseSTTDriver):
    def __init__(self, driver_id="test.stt.driver", models=()):
        super().__init__(driver_id, "Test STT Driver")
        self._supported_models = tuple(models)
        self.loaded = False
        self.unloaded = False
        self.transcribe_calls = []

    @property
    def supported_models(self) -> tuple[str, ...]:
        return self._supported_models

    async def load(self):
        self.loaded = True

    async def unload(self):
        self.unloaded = True

    def transcribe(self, audio_data, **kwargs):
        self.transcribe_calls.append(audio_data)
        return {"text": "hello test", "language": "zh", "confidence": 1.0}


def make_manager(selected_provider=None) -> STTPluginManager:
    return STTPluginManager(ConfigStub(selected_provider=selected_provider))


def test_stt_manager_initialization():
    manager = make_manager()

    assert manager.iter_drivers() == ()
    assert manager.active_driver_id == "none"
    assert manager.loading_status == "idle"


def test_stt_driver_registration():
    manager = make_manager()
    driver = FakeSTTDriver()

    manager.register_driver(driver)

    assert manager.has_driver(driver.id) is True
    assert manager.get_driver(driver.id) is driver


def test_stt_driver_config_updates_use_provider_host_boundary():
    manager = make_manager()
    driver = FakeSTTDriver()
    manager.register_driver(driver)

    config = manager.update_driver_config(driver.id, "model_size", "base")

    assert config["model_size"] == "base"
    assert driver.config["model_size"] == "base"


def test_stt_provider_snapshot_keeps_intent_and_runtime_state_separate():
    manager = make_manager()
    driver = FakeSTTDriver()
    manager.register_driver(driver)

    state = manager.snapshot_provider_state(driver.id)

    assert state["enabled"] is True
    assert state["desired_enabled"] is True
    assert state["active"] is False
    assert state["active_status"] == "stopped"


@pytest.mark.anyio
async def test_stt_startup_requires_selected_provider():
    manager = make_manager()
    driver = FakeSTTDriver("driver.stt.sensevoice")

    with patch(
        "services.managers.driver_loader.DriverPluginLoader.load_plugins",
        return_value=[driver],
    ):
        await manager.register_drivers()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert manager.last_error == "No STT provider selected in configuration"


@pytest.mark.anyio
async def test_stt_startup_rejects_missing_selected_provider():
    manager = make_manager(selected_provider="driver.stt.sensevoice")
    driver = FakeSTTDriver("driver.stt.other")

    with patch(
        "services.managers.driver_loader.DriverPluginLoader.load_plugins",
        return_value=[driver],
    ):
        await manager.register_drivers()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert manager.last_error == "Configured STT provider not discovered: driver.stt.sensevoice"


@pytest.mark.anyio
async def test_stt_activate_requires_known_driver():
    manager = make_manager()
    manager.register_driver(FakeSTTDriver())

    with pytest.raises(ValueError, match="Unknown STT provider"):
        await manager.activate("missing.driver")


@pytest.mark.anyio
async def test_stt_activation_loads_driver():
    manager = make_manager()
    driver = FakeSTTDriver()
    manager.register_driver(driver)

    await manager.activate(driver.id)

    assert manager.active_driver is driver
    assert manager.active_driver_id == driver.id
    assert driver.loaded is True


@pytest.mark.anyio
async def test_stt_model_switch_uses_driver_contract():
    manager = make_manager()
    driver = FakeSTTDriver(models=("tiny", "base", "large"))
    manager.register_driver(driver)

    await manager.switch_model_background("tiny")

    assert manager.active_driver is driver
    assert manager.model == "tiny"
    assert driver.config["model_size"] == "tiny"
    assert driver.unloaded is True
    assert driver.loaded is True


@pytest.mark.anyio
async def test_stt_unknown_switch_target_is_rejected():
    manager = make_manager()
    manager.register_driver(FakeSTTDriver())

    with pytest.raises(ValueError, match="Unknown STT provider"):
        await manager.switch_model_background("missing.driver")


@pytest.mark.anyio
async def test_stt_unload_active_driver_uses_contract():
    manager = make_manager()
    driver = FakeSTTDriver()
    manager.register_driver(driver)
    await manager.activate(driver.id)

    await manager.unload_active_driver()

    assert manager.active_driver is None
    assert manager.active_driver_id == "none"
    assert driver.unloaded is True


@pytest.mark.anyio
async def test_stt_transcribe_delegation():
    manager = make_manager()
    driver = FakeSTTDriver()
    manager.register_driver(driver)
    await manager.activate(driver.id)

    result = manager.transcribe(b"fake_audio")

    assert result["text"] == "hello test"
    assert driver.transcribe_calls == [b"fake_audio"]
