import pytest
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from services.provider_config_service import ProviderConfigService


class ConfigStub:
    def __init__(self):
        self.capabilities = SimpleNamespace(settings={})
        self.saved = 0

    def save(self):
        self.saved += 1


@pytest.mark.anyio
async def test_ensure_worker_running_skips_main_runtime():
    container = MagicMock()
    service = ProviderConfigService(container)

    assert await service.ensure_worker_running("main") is True
    container.get_process_manager.assert_not_called()


@pytest.mark.anyio
async def test_ensure_worker_running_starts_worker_runtime():
    process_manager = MagicMock()
    process_manager.is_running.return_value = False
    process_manager.start_worker.return_value = True

    container = MagicMock()
    container.get_process_manager.return_value = process_manager
    service = ProviderConfigService(container)

    assert await service.ensure_worker_running("worker:stt") is True
    process_manager.is_running.assert_called_once_with("worker:stt")
    process_manager.start_worker.assert_called_once_with("worker:stt")


@pytest.mark.anyio
async def test_update_config_persists_main_runtime_provider_setting():
    config = ConfigStub()
    manifest = SimpleNamespace(runtime_target="main")

    capability_module_manager = MagicMock()
    capability_module_manager.get_manifest.return_value = manifest

    container = MagicMock()
    container.get_config.return_value = config
    container.get_capability_module_manager.return_value = capability_module_manager

    service = ProviderConfigService(container)

    result = await service.update_config("provider.main", "enabled", True)

    assert result == {"success": True}
    assert config.capabilities.settings == {"provider.main": {"enabled": True}}
    assert config.saved == 1


@pytest.mark.anyio
async def test_update_config_broadcasts_worker_runtime_provider_setting():
    config = ConfigStub()
    manifest = SimpleNamespace(runtime_target="worker:tts")

    capability_module_manager = MagicMock()
    capability_module_manager.get_manifest.return_value = manifest

    process_manager = MagicMock()
    process_manager.is_running.return_value = True

    container = MagicMock()
    container.get_config.return_value = config
    container.get_process_manager.return_value = process_manager
    container.get_capability_module_manager.return_value = capability_module_manager

    hub = MagicMock()
    hub.broadcast_config_update = AsyncMock()
    fake_worker_control_hub = types.ModuleType("services.infra.worker_control_hub")
    fake_worker_control_hub.get_worker_control_hub = MagicMock(return_value=hub)

    service = ProviderConfigService(container)

    with patch.dict(sys.modules, {"services.infra.worker_control_hub": fake_worker_control_hub}):
        result = await service.update_config("driver.tts.edge", "voice", "zh-CN-XiaoxiaoNeural")

    assert result == {"success": True}
    hub.broadcast_config_update.assert_awaited_once()
    payload = hub.broadcast_config_update.await_args.kwargs
    assert payload["runtime_target"] == "worker:tts"
    assert payload["data"]["provider_id"] == "driver.tts.edge"
    assert payload["data"]["settings"] == {"voice": "zh-CN-XiaoxiaoNeural"}
