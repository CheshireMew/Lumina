"""
REAL pytest tests for PluginService - Testing actual plugin system

This tests REAL plugin management: listing, toggling, and configuration.
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

from services.plugin_service import PluginService
from core.protocol import EventType

@pytest.fixture
def mock_container():
    container = MagicMock()
    container.event_bus = MagicMock()
    container.event_bus.emit = AsyncMock() # Must be AsyncMock for await
    
    # Mock get_service to return a mock heartbeat service
    mock_heartbeat = MagicMock()
    mock_heartbeat.tickers = {}
    container.event_bus.get_service.return_value = mock_heartbeat
    
    return container

@pytest.mark.asyncio
async def test_plugin_service_list_all_plugins(mock_container):
    """Test merging states from registry and aggregator."""
    service = PluginService(mock_container)
    
    # Mock registry
    service.plugin_registry = {
        "plugin_1": {"id": "plugin_1", "enabled": True, "active_status": "ready"}
    }
    
    # Mock aggregator
    mock_aggregator = MagicMock()
    mock_aggregator.get_snapshot.return_value = [ # Changed from AsyncMock to direct return_value
        {"id": "plugin_1", "enabled": True, "active_status": "ready"},
        {"id": "plugin_2", "active_status": "error"}
    ]
    service._aggregator = mock_aggregator
    service._aggregator_ready = True
    
    plugins = await service.list_all_plugins()
    assert len(plugins) >= 2
    assert any(p["id"] == "plugin_1" for p in plugins)
    assert any(p["id"] == "plugin_2" for p in plugins)

@pytest.mark.asyncio
async def test_plugin_service_toggle_plugin(mock_container):
    """Test routing toggle requests via Lifecycle Bus."""
    service = PluginService(mock_container)
    
    # Mock list_all_plugins so it finds the plugin and thinks it's a worker plugin
    service.list_all_plugins = AsyncMock(return_value=[{"id": "plugin_1", "runtime_target": "worker"}])
    
    mock_bus = AsyncMock()
    # Mock httpx.AsyncClient to avoid connection errors when forwarding config to workers
    mock_client = AsyncMock()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_client.post.return_value = mock_res
    
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        with patch("httpx.AsyncClient", return_value=mock_client): # Added httpx patch
            # 1. Toggle ON
            await service.toggle_plugin("plugin_1", True)
            # It calls publish_state, not update_state
            mock_bus.publish_state.assert_called()
            
            # 2. Toggle OFF
            mock_bus.publish_state.reset_mock()
            await service.toggle_plugin("plugin_1", False)
            mock_bus.publish_state.assert_called()

@pytest.mark.asyncio
async def test_plugin_service_update_config(mock_container):
    """Test configuration updates via Lifecycle Bus."""
    service = PluginService(mock_container)
    
    # Mock list_all_plugins
    service.list_all_plugins = AsyncMock(return_value=[{"id": "plugin_1", "runtime_target": "worker"}])
    
    mock_bus = AsyncMock()
    # Mock httpx.AsyncClient to avoid connection errors when forwarding config to workers
    mock_client = AsyncMock()
    mock_res = MagicMock()
    mock_res.status_code = 200
    mock_client.post.return_value = mock_res
    
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        with patch("httpx.AsyncClient", return_value=mock_client):
            await service.update_config("plugin_1", "api_key", "secret_value")
            
            # For worker plugins, it calls the worker HTTP API directly and returns
            mock_client.post.assert_called()

@pytest.mark.asyncio
async def test_plugin_service_lifecycle_shout_sync(mock_container):
    """Test that shouting updates the local registry."""
    service = PluginService(mock_container)
    
    mock_bus = MagicMock()
    
    # Create an async generator for the shout subscription
    async def mock_shouts():
        yield {
            "worker_id": "worker_1",
            "plugins": [{"id": "plugin_1", "active_status": "ready"}]
        }
        # Yield once and stop
    
    mock_bus.subscribe_lifecycle_shouts.return_value = mock_shouts()
    
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        # Trigger the sync
        await service._start_lifecycle_sync()
        
        assert "plugin_1" in service.plugin_registry
        assert service.plugin_registry["plugin_1"]["active_status"] == "ready"

@pytest.mark.asyncio
async def test_plugin_service_ensure_worker_running(mock_container):
    """Test triggering worker provisioning via ProcessManager."""
    service = PluginService(mock_container)
    
    mock_pm = MagicMock()
    mock_pm.is_running.return_value = False
    mock_pm.start_worker.return_value = True
    mock_container.get_process_manager.return_value = mock_pm
    
    success = await service.ensure_worker_running("stt_server")
    
    assert success is True
    mock_pm.start_worker.assert_called_with("stt_server", "backend_launcher.py", ["stt"])

@pytest.mark.asyncio
async def test_plugin_service_register_capabilities(mock_container):
    """Test registering capabilities from worker heartbeats."""
    service = PluginService(mock_container)
    
    capabilities = [
        {
            "id": "plugin_1", 
            "type": "skill", 
            "name": "Test Tool",
            "category": "skill",
            "runtime_target": "worker"
        }
    ]
    
    await service.register_capabilities("worker_1", capabilities, host="127.0.0.2", port=9000)
    
    # Assert on plugin_registry, not worker_registry
    assert "plugin_1" in service.plugin_registry
    assert service.plugin_registry["plugin_1"]["name"] == "Test Tool"
    assert service.plugin_registry["plugin_1"]["worker_id"] == "worker_1"


