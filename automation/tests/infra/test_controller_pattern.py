import pytest
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

from services.plugin_service import PluginService


class ConfigStub:
    def __init__(self):
        self.plugins = SimpleNamespace(settings={})
        self.saved = 0

    def save(self):
        self.saved += 1


@pytest.mark.anyio
async def test_ensure_worker_running_skips_main_runtime():
    container = MagicMock()
    service = PluginService(container)

    assert await service.ensure_worker_running("main") is True
    container.get_process_manager.assert_not_called()


@pytest.mark.anyio
async def test_ensure_worker_running_starts_worker_runtime():
    process_manager = MagicMock()
    process_manager.is_running.return_value = False
    process_manager.start_worker.return_value = True

    container = MagicMock()
    container.get_process_manager.return_value = process_manager
    service = PluginService(container)

    assert await service.ensure_worker_running("worker:stt") is True
    process_manager.is_running.assert_called_once_with("worker:stt")
    process_manager.start_worker.assert_called_once_with("worker:stt")


@pytest.mark.anyio
async def test_update_config_persists_main_runtime_plugin_setting():
    config = ConfigStub()
    manifest = SimpleNamespace(runtime_target="main")

    system_plugin_manager = MagicMock()
    system_plugin_manager.get_manifest.return_value = manifest

    container = MagicMock()
    container.get_config.return_value = config
    container.get_system_plugin_manager.return_value = system_plugin_manager
    container.get_plugin_state_aggregator.return_value = None

    service = PluginService(container)

    result = await service.update_config("plugin.main", "enabled", True)

    assert result == {"success": True}
    assert config.plugins.settings == {"plugin.main": {"enabled": True}}
    assert config.saved == 1


@pytest.mark.anyio
async def test_update_config_broadcasts_worker_runtime_plugin_setting():
    config = ConfigStub()
    manifest = SimpleNamespace(runtime_target="worker:tts")

    system_plugin_manager = MagicMock()
    system_plugin_manager.get_manifest.return_value = manifest

    process_manager = MagicMock()
    process_manager.is_running.return_value = True

    container = MagicMock()
    container.get_config.return_value = config
    container.get_process_manager.return_value = process_manager
    container.get_system_plugin_manager.return_value = system_plugin_manager
    container.get_plugin_state_aggregator.return_value = None

    hub = MagicMock()
    hub.broadcast_config_update = AsyncMock()
    fake_worker_control_hub = types.ModuleType("services.infra.worker_control_hub")
    fake_worker_control_hub.get_worker_control_hub = MagicMock(return_value=hub)

    service = PluginService(container)

    with patch.dict(sys.modules, {"services.infra.worker_control_hub": fake_worker_control_hub}):
        result = await service.update_config("driver.tts.edge", "voice", "zh-CN-XiaoxiaoNeural")

    assert result == {"success": True}
    hub.broadcast_config_update.assert_awaited_once()
    payload = hub.broadcast_config_update.await_args.kwargs
    assert payload["runtime_target"] == "worker:tts"
    assert payload["data"]["plugin_id"] == "driver.tts.edge"
    assert payload["data"]["settings"] == {"voice": "zh-CN-XiaoxiaoNeural"}
