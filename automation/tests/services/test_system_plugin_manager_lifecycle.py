import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.events.bus import EventBus, EventSchema
from core.events.definitions import PluginLifecycleRequest
from services.system_plugin_manager import SystemPluginManager


def _build_manager(event_bus: EventBus) -> SystemPluginManager:
    container = MagicMock()
    container.has_service.side_effect = lambda name: name in {"event_bus", "config"}
    container.get_event_bus.return_value = event_bus
    container.get_capability_registry.return_value = None
    container.get_config.return_value = MagicMock()
    container.get_capability_package_registry.return_value = None
    return SystemPluginManager(container=container)


@pytest.mark.anyio
async def test_lifecycle_enable_request_uses_typed_payload():
    event_bus = EventBus()
    event_bus.register_schema(
        "plugin.lifecycle.request_enable",
        EventSchema("1.0", PluginLifecycleRequest),
    )
    manager = _build_manager(event_bus)
    manager.enable_plugin = AsyncMock(return_value=True)
    manager._subscribe_lifecycle_requests()

    await event_bus.emit(
        "plugin.lifecycle.request_enable",
        PluginLifecycleRequest(plugin_id="plugin.lifecycle.test"),
    )

    manager.enable_plugin.assert_awaited_once_with("plugin.lifecycle.test")


@pytest.mark.anyio
async def test_lifecycle_enable_request_rejects_untyped_payload():
    event_bus = EventBus()
    event_bus.register_schema(
        "plugin.lifecycle.request_enable",
        EventSchema("1.0", PluginLifecycleRequest),
    )
    manager = _build_manager(event_bus)
    manager.enable_plugin = AsyncMock(return_value=True)
    manager._subscribe_lifecycle_requests()

    await event_bus.emit(
        "plugin.lifecycle.request_enable",
        {"plugin_id": "plugin.lifecycle.test"},
    )

    manager.enable_plugin.assert_not_awaited()
