import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from capabilities.vision.manager import VisionPluginManager
from core.interfaces.driver import BaseVisionDriver


class ConfigStub:
    def __init__(self, selected_provider=None):
        self.selected_provider = selected_provider

    def get_selected_provider(self, _capability):
        return self.selected_provider

    def is_provider_desired_enabled(self, _provider_id):
        return True

    def get_provider_settings(self, _provider_id):
        return {}


class FakeVisionDriver(BaseVisionDriver):
    def __init__(self, driver_id="driver.vision.fake"):
        super().__init__(driver_id, "Fake Vision Driver")
        self.loaded = False
        self.unloaded = False

    async def load(self):
        self.loaded = True

    def unload(self):
        self.unloaded = True

    async def analyze(self, image, prompt: str = "Describe this image.") -> str:
        return f"{self.id}:{prompt}"


def test_screen_capture_packet():
    service = VisionPluginManager(config=ConfigStub())
    mock_instance = MagicMock()
    mock_instance.monitors = [None, {"top": 0, "left": 0, "width": 1920, "height": 1080}]
    service.mss = mock_instance
    service._mss_tools = MagicMock()
    service._mss_tools.to_png.return_value = b"fake_png_bytes"

    mock_img = MagicMock()
    mock_img.rgb = b"fake_rgb_data"
    mock_img.size = (1920, 1080)
    mock_instance.grab.return_value = mock_img

    b64_result = service.capture_screen_base64()

    assert b64_result is not None
    assert b64_result.startswith("data:image/png;base64,")


@pytest.mark.anyio
async def test_vision_activation_requires_known_driver():
    service = VisionPluginManager(config=ConfigStub())
    service.register_driver(FakeVisionDriver())

    with pytest.raises(ValueError, match="Unknown VISION provider"):
        await service.activate("missing.driver")

    assert service.active_driver is None
    assert service.active_driver_id == "none"


@pytest.mark.anyio
async def test_vision_startup_requires_selected_provider():
    service = VisionPluginManager(config=ConfigStub())
    service.register_driver(FakeVisionDriver("driver.vision.moondream"))

    await service.register_drivers()

    assert service.active_driver is None
    assert service.active_driver_id == "none"
    assert service.last_error == "No VISION provider selected in configuration"


@pytest.mark.anyio
async def test_vision_startup_rejects_missing_selected_provider():
    service = VisionPluginManager(config=ConfigStub(selected_provider="driver.vision.moondream"))
    service.register_driver(FakeVisionDriver("driver.vision.other"))

    await service.register_drivers()

    assert service.active_driver is None
    assert service.active_driver_id == "none"
    assert service.last_error == "Configured VISION provider not discovered: driver.vision.moondream"


@pytest.mark.anyio
async def test_vision_startup_activates_selected_provider():
    driver = FakeVisionDriver("driver.vision.other")
    service = VisionPluginManager(config=ConfigStub(selected_provider=driver.id))
    service.register_driver(driver)

    await service.register_drivers()

    assert service.active_driver is driver
    assert service.active_driver_id == driver.id
    assert driver.loaded is True
