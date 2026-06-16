"""
REAL integration test for TTSManager.
Tests driver registration and activation flow.
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

from services.managers.tts import TTSPluginManager


class ConfigStub:
    def get_selected_provider(self, _capability):
        return None

    def is_plugin_desired_enabled(self, _plugin_id):
        return True

@pytest.mark.anyio
async def test_tts_manager_driver_discovery():
    tm = TTSPluginManager(ConfigStub())
    
    # Mock driver plugin discovery
    with patch("services.managers.driver_loader.DriverPluginLoader.load_plugins") as mock_load:
        mock_driver = MagicMock()
        mock_driver.id = "test.tts.driver"
        mock_driver.name = "Test TTS"
        mock_load.return_value = [mock_driver]
        
        await tm.load_driver_plugins()
        
        assert "test.tts.driver" in tm.drivers
        assert tm.active_driver is None

@pytest.mark.anyio
async def test_tts_manager_activation():
    tm = TTSPluginManager(ConfigStub())
    
    mock_driver = MagicMock()
    mock_driver.id = "test.tts.driver"
    mock_driver.load = AsyncMock()
    
    tm.register_driver(mock_driver)
    
    await tm.activate("test.tts.driver")
    
    assert tm.active_driver_id == "test.tts.driver"
    assert tm.active_driver == mock_driver
    mock_driver.load.assert_called_once()

@pytest.mark.anyio
async def test_tts_manager_unload():
    tm = TTSPluginManager(ConfigStub())
    mock_driver = MagicMock()
    mock_driver.unload = AsyncMock()
    
    tm.active_driver = mock_driver
    tm.active_driver_id = "test.tts.active"
    
    await tm.unload_active_driver()
    
    assert tm.active_driver is None
    assert tm.active_driver_id == "none"
    mock_driver.unload.assert_called_once()
