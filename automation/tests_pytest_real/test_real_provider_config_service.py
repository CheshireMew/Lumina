import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.provider_config_service import ProviderConfigService
from services.config_service import ConfigService
from config.models import CapabilitiesConfig


class ConfigStub:
    def __init__(self):
        self.capabilities = CapabilitiesConfig(settings={})
        self.saved = 0

    def replace_sections(self, *, persist=True, **sections):
        for key, value in sections.items():
            setattr(self, key, value)
        if persist:
            self.saved += 1


def build_service(config=None, process_manager=None, hub=None):
    config = config or ConfigStub()
    process_manager = process_manager or MagicMock()
    hub = hub or MagicMock()
    return ProviderConfigService(
        config=config,
        process_manager=process_manager,
        worker_control_hub=hub,
        config_service=ConfigService(config, MagicMock()),
    )


@pytest.mark.anyio
async def test_provider_config_service_ensure_worker_running_skips_main():
    process_manager = MagicMock()
    service = build_service(process_manager=process_manager)

    assert await service.ensure_worker_running("main") is True
    process_manager.is_running.assert_not_called()


@pytest.mark.anyio
async def test_provider_config_service_ensure_worker_running_uses_process_manager():
    process_manager = MagicMock()
    process_manager.is_running.return_value = False
    process_manager.start_worker.return_value = True
    service = build_service(process_manager=process_manager)

    assert await service.ensure_worker_running("worker:stt") is True
    process_manager.is_running.assert_called_once_with("worker:stt")
    process_manager.start_worker.assert_called_once_with("worker:stt")


@pytest.mark.anyio
async def test_provider_config_service_update_config_for_main_runtime():
    config = ConfigStub()

    service = build_service(config=config)

    result = await service.update_config("provider.main", "api_key", "secret")

    assert result == {"success": True}
    assert config.capabilities.settings == {"provider.main": {"api_key": "secret"}}
    assert config.saved == 1


@pytest.mark.anyio
async def test_provider_config_service_update_config_for_worker_runtime():
    config = ConfigStub()

    process_manager = MagicMock()
    process_manager.is_running.return_value = True

    hub = MagicMock()
    hub.broadcast_config_update = AsyncMock()
    service = build_service(config=config, process_manager=process_manager, hub=hub)

    result = await service.update_config("driver.tts.edge", "voice", "test-voice")

    assert result == {"success": True}
    hub.broadcast_config_update.assert_awaited_once()
    kwargs = hub.broadcast_config_update.await_args.kwargs
    assert kwargs["runtime_target"] == "worker:tts"
    assert kwargs["data"]["settings"] == {"voice": "test-voice"}
