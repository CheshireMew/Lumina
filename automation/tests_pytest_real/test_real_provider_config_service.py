import sys
import types
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.provider_config_service import ProviderConfigService


class ConfigStub:
    def __init__(self):
        self.capabilities = SimpleNamespace(settings={})
        self.saved = 0

    def save(self):
        self.saved += 1


@pytest.fixture
def container():
    return MagicMock()


@pytest.mark.anyio
async def test_provider_config_service_ensure_worker_running_skips_main(container):
    service = ProviderConfigService(container)

    assert await service.ensure_worker_running("main") is True
    container.get_process_manager.assert_not_called()


@pytest.mark.anyio
async def test_provider_config_service_ensure_worker_running_uses_process_manager(container):
    process_manager = MagicMock()
    process_manager.is_running.return_value = False
    process_manager.start_worker.return_value = True
    container.get_process_manager.return_value = process_manager

    service = ProviderConfigService(container)

    assert await service.ensure_worker_running("worker:stt") is True
    process_manager.is_running.assert_called_once_with("worker:stt")
    process_manager.start_worker.assert_called_once_with("worker:stt")


@pytest.mark.anyio
async def test_provider_config_service_update_config_for_main_runtime(container):
    config = ConfigStub()

    container.get_config.return_value = config

    service = ProviderConfigService(container)

    result = await service.update_config("provider.main", "api_key", "secret")

    assert result == {"success": True}
    assert config.capabilities.settings == {"provider.main": {"api_key": "secret"}}
    assert config.saved == 1


@pytest.mark.anyio
async def test_provider_config_service_update_config_for_worker_runtime(container):
    config = ConfigStub()

    process_manager = MagicMock()
    process_manager.is_running.return_value = True

    container.get_config.return_value = config
    container.get_process_manager.return_value = process_manager

    hub = MagicMock()
    hub.broadcast_config_update = AsyncMock()
    fake_worker_control_hub = types.ModuleType("services.infra.worker_control_hub")
    fake_worker_control_hub.get_worker_control_hub = MagicMock(return_value=hub)

    service = ProviderConfigService(container)

    with patch.dict(sys.modules, {"services.infra.worker_control_hub": fake_worker_control_hub}):
        result = await service.update_config("driver.tts.edge", "voice", "test-voice")

    assert result == {"success": True}
    hub.broadcast_config_update.assert_awaited_once()
    kwargs = hub.broadcast_config_update.await_args.kwargs
    assert kwargs["runtime_target"] == "worker:tts"
    assert kwargs["data"]["settings"] == {"voice": "test-voice"}
