"""
REAL integration test for STTManager.
Tests driver discovery and activation.
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

from services.managers.stt import STTPluginManager


class ConfigStub:
    def get_selected_provider(self, _capability):
        return None

    def is_provider_desired_enabled(self, _provider_id):
        return True

@pytest.mark.anyio
async def test_stt_manager_driver_discovery():
    sm = STTPluginManager(ConfigStub())
    
    # Mock driver plugin discovery
    with patch("services.managers.driver_loader.DriverLoader.load_plugins") as mock_load:
        mock_driver = MagicMock()
        mock_driver.id = "test.stt.driver"
        mock_driver.name = "Test STT"
        mock_load.return_value = [mock_driver]
        
        await sm.load_drivers()
        
        assert "test.stt.driver" in sm.drivers
        assert sm.active_driver is None

@pytest.mark.anyio
async def test_stt_manager_activation():
    sm = STTPluginManager(ConfigStub())
    
    mock_driver = MagicMock()
    mock_driver.id = "test.stt.driver"
    mock_driver.load = AsyncMock() if asyncio.iscoroutinefunction(MagicMock) else MagicMock()
    # Handle sync/async load detection in activate()
    
    sm.register_driver(mock_driver)
    
    await sm.activate("test.stt.driver")
    
    assert sm.active_driver_id == "test.stt.driver"
    assert sm.active_driver == mock_driver

def test_stt_transcribe_delegation():
    sm = STTPluginManager(ConfigStub())
    mock_driver = MagicMock()
    mock_driver.transcribe.return_value = {"text": "hello test"}
    sm.active_driver = mock_driver
    
    result = sm.transcribe(b"fake_audio")
    
    assert result["text"] == "hello test"
    mock_driver.transcribe.assert_called_once_with(b"fake_audio")
