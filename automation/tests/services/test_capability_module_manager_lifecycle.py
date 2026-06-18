import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.events.bus import EventBus, EventSchema
from core.events.definitions import CapabilityLifecycleRequest
from services.capability_registry import CapabilityRegistry
from services.capability_module_manager import CapabilityModuleManager


def _build_manager(event_bus: EventBus) -> CapabilityModuleManager:
    container = MagicMock()
    container.has_service.side_effect = lambda name: name in {"event_bus", "config"}
    container.get_event_bus.return_value = event_bus
    container.get_capability_registry.return_value = CapabilityRegistry()
    container.get_config.return_value = MagicMock()
    container.get_worker_runtime_registry.return_value = MagicMock()
    return CapabilityModuleManager(container=container)


@pytest.mark.anyio
async def test_lifecycle_enable_request_uses_typed_payload():
    event_bus = EventBus()
    event_bus.register_schema(
        "capability.lifecycle.request_enable",
        EventSchema("1.0", CapabilityLifecycleRequest),
    )
    manager = _build_manager(event_bus)
    manager.enable_module = AsyncMock(return_value=True)
    manager._subscribe_lifecycle_requests()

    await event_bus.emit(
        "capability.lifecycle.request_enable",
        CapabilityLifecycleRequest(module_id="capability.lifecycle.test"),
    )

    manager.enable_module.assert_awaited_once_with("capability.lifecycle.test")


@pytest.mark.anyio
async def test_lifecycle_enable_request_rejects_untyped_payload():
    event_bus = EventBus()
    event_bus.register_schema(
        "capability.lifecycle.request_enable",
        EventSchema("1.0", CapabilityLifecycleRequest),
    )
    manager = _build_manager(event_bus)
    manager.enable_module = AsyncMock(return_value=True)
    manager._subscribe_lifecycle_requests()

    await event_bus.emit(
        "capability.lifecycle.request_enable",
        {"module_id": "capability.lifecycle.test"},
    )

    manager.enable_module.assert_not_awaited()
