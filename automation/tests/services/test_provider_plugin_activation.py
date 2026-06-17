import importlib
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


class ConfigStub:
    def __init__(self, selected_provider):
        self.selected_provider = selected_provider
        self.memory = SimpleNamespace(
            model_dump=MagicMock(
                return_value={
                    "provider": "driver.memory.postgres",
                    "postgres": {
                        "host": "127.0.0.1",
                        "port": 5432,
                        "user": "lumina",
                        "password": "",
                        "database": "lumina",
                    },
                },
            ),
        )

    def get_selected_provider(self, _capability):
        return self.selected_provider


class ContextStub:
    def __init__(self, capability, selected_provider, manager=None):
        self.config = ConfigStub(selected_provider)
        if manager is None:
            manager = MagicMock()
            manager.activate = AsyncMock()
        self.manager = manager
        self.manager.active_driver = None
        self.capability = capability

    def get_config(self):
        return {}

    def get_service(self, name):
        if name == "config":
            return self.config
        if name == self.capability:
            return self.manager
        raise AttributeError(name)


async def _enable_capability(module_name: str, module_id: str, capability: str, selected_provider):
    module = importlib.import_module(module_name)
    capability_module = module.Capability()
    capability_module._bind_manifest(SimpleNamespace(id=module_id))
    context = ContextStub(capability, selected_provider)
    await capability_module.load(context)
    await capability_module.enable()
    return context.manager


@pytest.mark.anyio
async def test_stt_provider_plugin_registers_without_autoselecting_unselected_provider():
    manager = await _enable_capability(
        "capability_modules.stt_sensevoice.module",
        "driver.stt.sensevoice",
        "stt",
        selected_provider="driver.stt.other",
    )

    manager.register_driver.assert_called_once()
    manager.activate.assert_not_awaited()


@pytest.mark.anyio
async def test_stt_provider_plugin_activates_selected_provider():
    manager = await _enable_capability(
        "capability_modules.stt_sensevoice.module",
        "driver.stt.sensevoice",
        "stt",
        selected_provider="driver.stt.sensevoice",
    )

    manager.register_driver.assert_called_once()
    manager.activate.assert_awaited_once_with("driver.stt.sensevoice")


@pytest.mark.anyio
async def test_tts_provider_plugin_registers_without_autoselecting_unselected_provider():
    edge_tts_stub = SimpleNamespace(
        list_voices=AsyncMock(return_value=[]),
        exceptions=SimpleNamespace(NoAudioReceived=Exception),
        Communicate=MagicMock(),
    )
    with patch.dict(sys.modules, {"edge_tts": edge_tts_stub}):
        manager = await _enable_capability(
            "capability_modules.tts_edge.module",
            "driver.tts.edge",
            "tts",
            selected_provider="driver.tts.other",
        )

    manager.register_driver.assert_called_once()
    manager.activate.assert_not_awaited()


@pytest.mark.anyio
async def test_tts_provider_plugin_activates_selected_provider():
    edge_tts_stub = SimpleNamespace(
        list_voices=AsyncMock(return_value=[]),
        exceptions=SimpleNamespace(NoAudioReceived=Exception),
        Communicate=MagicMock(),
    )
    with patch.dict(sys.modules, {"edge_tts": edge_tts_stub}):
        manager = await _enable_capability(
            "capability_modules.tts_edge.module",
            "driver.tts.edge",
            "tts",
            selected_provider="driver.tts.edge",
        )

    manager.register_driver.assert_called_once()
    manager.activate.assert_awaited_once_with("driver.tts.edge")


@pytest.mark.anyio
async def test_memory_provider_plugin_does_not_connect_unselected_provider():
    module = importlib.import_module("capability_modules.memory_postgres.module")
    capability_module = module.Capability()
    capability_module._bind_manifest(SimpleNamespace(id="driver.memory.postgres"))
    memory_service = MagicMock()
    context = ContextStub(
        "memory",
        selected_provider="driver.memory.other",
        manager=memory_service,
    )

    await capability_module.load(context)
    with patch.object(module.MemoryDriverFactory, "create_driver") as create_driver:
        await capability_module.enable()

    create_driver.assert_not_called()
    memory_service.replace_driver.assert_not_called()


@pytest.mark.anyio
async def test_memory_provider_plugin_connects_selected_provider():
    module = importlib.import_module("capability_modules.memory_postgres.module")
    capability_module = module.Capability()
    capability_module._bind_manifest(SimpleNamespace(id="driver.memory.postgres"))
    next_driver = MagicMock()
    next_driver.connect = AsyncMock()
    memory_service = MagicMock()
    memory_service.is_driver_active.return_value = False
    memory_service.replace_driver = AsyncMock()
    context = ContextStub(
        "memory",
        selected_provider="driver.memory.postgres",
        manager=memory_service,
    )

    await capability_module.load(context)
    with patch.object(module.MemoryDriverFactory, "create_driver", return_value=next_driver) as create_driver:
        await capability_module.enable()

    create_driver.assert_called_once_with(
        "driver.memory.postgres",
        driver_config=context.config.memory.model_dump.return_value,
    )
    next_driver.connect.assert_awaited_once()
    memory_service.replace_driver.assert_awaited_once_with(next_driver)
