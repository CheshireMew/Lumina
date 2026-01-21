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

@pytest.mark.asyncio
async def test_plugin_sync_filtering_by_target():
    mock_pm = MagicMock()
    mock_pm.enable_plugin = AsyncMock()
    
    # Expecting only "stt_server" updates
    sync = PluginStateSync(mock_pm, expected_target="stt_server")
    
    # 1. Update matching target
    await sync._handle_state_update("plugin_1", {"desired_enabled": True, "runtime_target": "stt_server"})
    mock_pm.enable_plugin.assert_called_once_with("plugin_1")
    
    # 2. Update NOT matching target
    mock_pm.enable_plugin.reset_mock()
    await sync._handle_state_update("plugin_2", {"desired_enabled": True, "runtime_target": "tts_server"})
    mock_pm.enable_plugin.assert_not_called()

@pytest.mark.asyncio
async def test_plugin_sync_disable_plugin():
    mock_pm = MagicMock()
    mock_pm.disable_plugin = AsyncMock()
    
    sync = PluginStateSync(mock_pm)
    
    await sync._handle_state_update("plugin_1", {"desired_enabled": False})
    mock_pm.disable_plugin.assert_called_once_with("plugin_1")

@pytest.mark.asyncio
async def test_plugin_sync_reporter_trigger():
    mock_pm = MagicMock()
    mock_pm.enable_plugin = AsyncMock() # Must be AsyncMock
    mock_reporter = MagicMock()
    mock_reporter.force_report = AsyncMock()
    
    sync = PluginStateSync(mock_pm, reporter=mock_reporter)
    
    await sync._handle_state_update("plugin_1", {"desired_enabled": True})

    
    # Check if force_report task was created
    # Since it's create_task, we might need a small sleep or check task creation
    await asyncio.sleep(0.01)
    mock_reporter.force_report.assert_called_once()
