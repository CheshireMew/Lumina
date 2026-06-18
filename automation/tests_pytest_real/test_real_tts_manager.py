"""
REAL integration test for TTSManager.
Tests driver registration and activation flow.
"""
import sys
import os
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.managers.tts import TTSProviderManager


class ConfigStub:
    def get_selected_provider(self, _capability):
        return None

    def is_provider_desired_enabled(self, _provider_id):
        return True

@pytest.mark.anyio
async def test_tts_manager_driver_discovery():
    tm = TTSProviderManager(ConfigStub())

    await tm.load_drivers()

    assert "driver.tts.edge" in tm.drivers
    assert tm.active_driver is None

@pytest.mark.anyio
async def test_tts_manager_activation():
    tm = TTSProviderManager(ConfigStub())
    
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
    tm = TTSProviderManager(ConfigStub())
    mock_driver = MagicMock()
    mock_driver.unload = AsyncMock()
    
    tm.active_driver = mock_driver
    tm.active_driver_id = "test.tts.active"
    
    await tm.unload_active_driver()
    
    assert tm.active_driver is None
    assert tm.active_driver_id == "none"
    mock_driver.unload.assert_called_once()
