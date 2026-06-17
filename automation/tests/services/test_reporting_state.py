import sys
from pathlib import Path
from unittest.mock import MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.reporting.driver_state_collector import DriverStateCollector
from services.reporting.runtime_state_provider import build_runtime_state_provider


def test_driver_state_collector_uses_provider_host_snapshot():
    manager = MagicMock()
    manager.iter_drivers.return_value = (("driver.stt.test", object()),)
    manager.snapshot_provider_state.return_value = {
        "id": "driver.stt.test",
        "name": "Test STT",
        "description": "Driver state",
        "enabled": True,
        "desired_enabled": True,
        "active": True,
        "active_status": "ready",
        "active_in_group": True,
        "permissions": [],
        "config_schema": None,
        "current_config": {"model": "base"},
        "is_driver": True,
        "driver_id": "driver.stt.test",
        "error": None,
        "load_time_ms": 12,
    }

    states = DriverStateCollector.gather_driver_states(
        manager=manager,
        category="stt",
        runtime_target="worker:stt",
        service_url="http://127.0.0.1:8765/lipp/lifecycle",
    )

    manager.iter_drivers.assert_called_once_with()
    manager.snapshot_provider_state.assert_called_once_with("driver.stt.test")
    assert states == [
        {
            "id": "driver.stt.test",
            "name": "Test STT",
            "description": "Driver state",
            "kind": "provider",
            "category": "stt",
            "group_id": "stt",
            "group_policy": "exclusive",
            "capabilities": ["stt"],
            "enabled": True,
            "desired_enabled": True,
            "active": True,
            "active_status": "ready",
            "computed_status": "running",
            "active_in_group": True,
            "runtime_target": "worker:stt",
            "permissions": [],
            "config_schema": None,
            "current_config": {"model": "base"},
            "is_driver": True,
            "service_url": "http://127.0.0.1:8765/lipp/lifecycle",
            "driver_id": "driver.stt.test",
            "error": None,
            "load_time_ms": 12,
        }
    ]


@pytest.mark.anyio
async def test_runtime_state_provider_uses_container_getter():
    module_manager = MagicMock()
    module_manager.list_modules.return_value = [{"id": "module.system", "name": "System"}]

    container = MagicMock()
    container.get_capability_module_manager.return_value = module_manager

    provider = build_runtime_state_provider(
        lambda: [{"id": "driver.stt.test", "name": "Driver"}],
        container=container,
    )

    states = await provider()

    container.get_capability_module_manager.assert_called_once_with()
    assert {state["id"] for state in states} == {"driver.stt.test", "module.system"}
