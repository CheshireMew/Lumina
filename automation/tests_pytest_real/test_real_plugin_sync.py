"""
REAL integration test for PluginStateSync.
Tests state update handling and filtering.
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.plugin_state_sync import PluginStateSync


class BusStub:
    async def connect(self):
        pass

    async def get_all_states(self):
        return {}

    async def subscribe_state(self, _callback):
        pass

    async def send_heartbeat(self, _worker_id):
        pass

@pytest.mark.anyio
async def test_plugin_sync_filtering_by_target():
    mock_pm = MagicMock()
    mock_pm.is_plugin_desired_enabled.return_value = True
    mock_pm.enable_plugin = AsyncMock()
    
    # Expecting only worker:stt updates
    sync = PluginStateSync(mock_pm, expected_target="worker:stt", bus=BusStub())
    
    # 1. Update matching target
    await sync._handle_state_update("plugin_1", {"desired_enabled": True, "runtime_target": "worker:stt"})
    mock_pm.enable_plugin.assert_called_once_with("plugin_1")
    
    # 2. Update NOT matching target
    mock_pm.enable_plugin.reset_mock()
    await sync._handle_state_update("plugin_2", {"desired_enabled": True, "runtime_target": "worker:tts"})
    mock_pm.enable_plugin.assert_not_called()

@pytest.mark.anyio
async def test_plugin_sync_disable_plugin():
    mock_pm = MagicMock()
    mock_pm.is_plugin_desired_enabled.return_value = False
    mock_pm.disable_plugin = AsyncMock()
    
    sync = PluginStateSync(mock_pm, bus=BusStub())
    
    await sync._handle_state_update("plugin_1", {"desired_enabled": False})
    mock_pm.disable_plugin.assert_called_once_with("plugin_1")

@pytest.mark.anyio
async def test_plugin_sync_reporter_trigger():
    mock_pm = MagicMock()
    mock_pm.is_plugin_desired_enabled.return_value = True
    mock_pm.enable_plugin = AsyncMock() # Must be AsyncMock
    mock_reporter = MagicMock()
    mock_reporter.force_report = AsyncMock()
    
    sync = PluginStateSync(mock_pm, reporter=mock_reporter, bus=BusStub())
    
    await sync._handle_state_update("plugin_1", {"desired_enabled": True})

    
    # Check if force_report task was created
    # Since it's create_task, we might need a small sleep or check task creation
    await asyncio.sleep(0.01)
    mock_reporter.force_report.assert_called_once()
