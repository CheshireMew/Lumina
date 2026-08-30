import pytest
from unittest.mock import AsyncMock, MagicMock

from config.models import CapabilitiesConfig
from services.config_service import ConfigService
from services.provider_config_service import ProviderConfigService


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
async def test_ensure_worker_running_skips_main_runtime():
    process_manager = MagicMock()
    service = build_service(process_manager=process_manager)

    assert await service.ensure_worker_running("main") is True
    process_manager.is_running.assert_not_called()


@pytest.mark.anyio
async def test_ensure_worker_running_starts_worker_runtime():
    process_manager = MagicMock()
    process_manager.is_running.return_value = False
    process_manager.start_worker.return_value = True

    service = build_service(process_manager=process_manager)

    assert await service.ensure_worker_running("worker:stt") is True
    process_manager.is_running.assert_called_once_with("worker:stt")
    process_manager.start_worker.assert_called_once_with("worker:stt")


@pytest.mark.anyio
async def test_update_config_persists_main_runtime_provider_setting():
    config = ConfigStub()

    service = build_service(config=config)

    result = await service.update_config("provider.main", "enabled", True)

    assert result == {"success": True}
    assert config.capabilities.settings == {"provider.main": {"enabled": True}}
    assert config.saved == 1


@pytest.mark.anyio
async def test_update_config_broadcasts_worker_runtime_provider_setting():
    config = ConfigStub()

    process_manager = MagicMock()
    process_manager.is_running.return_value = True

    hub = MagicMock()
    hub.broadcast_config_update = AsyncMock()
    service = build_service(config=config, process_manager=process_manager, hub=hub)

    result = await service.update_config("driver.tts.edge", "voice", "zh-CN-XiaoxiaoNeural")

    assert result == {"success": True}
    hub.broadcast_config_update.assert_awaited_once()
    payload = hub.broadcast_config_update.await_args.kwargs
    assert payload["runtime_target"] == "worker:tts"
    assert payload["data"]["provider_id"] == "driver.tts.edge"
    assert payload["data"]["settings"] == {"voice": "zh-CN-XiaoxiaoNeural"}
