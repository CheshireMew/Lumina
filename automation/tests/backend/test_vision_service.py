import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

from capabilities.vision.manager import VisionProviderManager
from core.interfaces.driver import BaseVisionDriver
from provider_drivers.vision_llm.drivers.vision import MultimodalLLMVisionDriver


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


class BrokenVisionDriver(FakeVisionDriver):
    async def load(self):
        raise RuntimeError("视觉路线缺少配置")


class LLMManagerStub:
    def __init__(self, *, provider_type="pollinations", api_key="", base_url="https://example.test/v1"):
        self.route = SimpleNamespace(model="vision-model")
        self.provider = SimpleNamespace(
            enabled=True,
            type=provider_type,
            api_key=api_key,
            base_url=base_url,
        )
        self.driver_requested = False

    def get_route(self, _feature):
        return self.route

    def get_provider_config(self, _feature):
        return self.provider

    async def get_driver(self, _feature):
        self.driver_requested = True
        return object()


def test_screen_capture_packet():
    service = VisionProviderManager(config=ConfigStub())
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
    service = VisionProviderManager(config=ConfigStub())
    service.register_driver(FakeVisionDriver())

    with pytest.raises(ValueError, match="Unknown VISION provider"):
        await service.activate("missing.driver")

    assert service.active_driver is None
    assert service.active_driver_id == "none"


@pytest.mark.anyio
async def test_vision_startup_requires_selected_provider():
    service = VisionProviderManager(config=ConfigStub())
    service.register_driver(FakeVisionDriver("driver.vision.moondream"))

    await service.register_drivers()

    assert service.active_driver is None
    assert service.active_driver_id == "none"
    assert service.last_error == "No VISION provider selected in configuration"


@pytest.mark.anyio
async def test_vision_startup_rejects_missing_selected_provider():
    service = VisionProviderManager(config=ConfigStub(selected_provider="driver.vision.moondream"))
    service.register_driver(FakeVisionDriver("driver.vision.other"))

    await service.register_drivers()

    assert service.active_driver is None
    assert service.active_driver_id == "none"
    assert service.last_error == "Configured VISION provider not discovered: driver.vision.moondream"


@pytest.mark.anyio
async def test_vision_startup_activates_selected_provider():
    driver = FakeVisionDriver("driver.vision.other")
    service = VisionProviderManager(config=ConfigStub(selected_provider=driver.id))
    service.register_driver(driver)

    await service.register_drivers()

    assert service.active_driver is driver
    assert service.active_driver_id == driver.id
    assert driver.loaded is True


@pytest.mark.anyio
async def test_vision_startup_stays_degraded_when_selected_provider_is_not_configured():
    driver = BrokenVisionDriver("driver.vision.broken")
    service = VisionProviderManager(config=ConfigStub(selected_provider=driver.id))
    service.register_driver(driver)

    await service.register_drivers()

    state = service.snapshot_provider_state(driver.id)
    assert service.active_driver is None
    assert state["active_status"] == "error"
    assert state["error"] == "视觉路线缺少配置"


@pytest.mark.anyio
async def test_multimodal_vision_rejects_pollinations_anonymous_route():
    llm_manager = LLMManagerStub()
    driver = MultimodalLLMVisionDriver(llm_manager)

    with pytest.raises(RuntimeError, match="匿名接口不支持图片输入"):
        await driver.load()

    assert llm_manager.driver_requested is False


@pytest.mark.anyio
async def test_multimodal_vision_accepts_explicit_multimodal_service_configuration():
    llm_manager = LLMManagerStub(provider_type="openai", api_key="local-key")
    driver = MultimodalLLMVisionDriver(llm_manager)

    await driver.load()

    assert llm_manager.driver_requested is True
