
import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from services.plugin_service import PluginService

@pytest.mark.asyncio
async def test_controller_register_capabilities_writes_actual():
    """Verify register_capabilities writes active_status to Bus (Actual State)."""
    mock_container = MagicMock()
    mock_container.system_plugin_manager = None
    mock_container.mcp_host = None
    mock_container.heartbeat_service = None
    
    svc = PluginService(mock_container)
    
    # Mock Bus
    mock_bus = AsyncMock()
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        # Action
        await svc.register_capabilities(
            worker_id="worker_1", 
            capabilities=[{
                "id": "plugin_a", 
                "active_status": "loading", 
                "enabled": True
            }]
        )
        
        # Verify
        # [Scheme C] Registry is Read-Only/Discovery. DB Write handled by WorkerStatusReporter.
        # Should NOT call publish_state.
        mock_bus.publish_state.assert_not_called()

@pytest.mark.asyncio
async def test_controller_toggle_writes_desired():
    """Verify toggle_plugin writes desired_enabled to Bus (Desired State)."""
    mock_container = MagicMock()
    svc = PluginService(mock_container)
    
    # Mock Registry to find plugin
    svc.plugin_registry = {
        "plugin_a": {
            "id": "plugin_a", 
            "runtime_target": "stt_server",
            "group_policy": "independent"
        }
    }
    
    # Mock Bus
    mock_bus = AsyncMock()
    
    # Mock list_all_plugins to return our registry
    svc.list_all_plugins = AsyncMock(return_value=[svc.plugin_registry["plugin_a"]])
    
    # Mock Service Discovery for get_url
    svc.worker_registry = {"stt_server": {"host": "127.0.0.1", "port": 8000}}
    svc.services.system_plugin_manager = MagicMock()
        
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        with patch("httpx.AsyncClient") as mock_http:
            # Mock HTTP response
            mock_resp = MagicMock()
            mock_resp.status_code = 200
            
            # Context manager mock
            mock_client = AsyncMock()
            mock_client.post.return_value = mock_resp
            mock_http.return_value.__aenter__.return_value = mock_client
            
            # Action
            await svc.toggle_plugin("plugin_a", True)
            
            # Verify Bus Update (The Controller Logic)
            mock_bus.publish_state.assert_called()
            call_args = mock_bus.publish_state.call_args[0]
            pid, state = call_args
            
            assert pid == "plugin_a"
            assert state["desired_enabled"] is True
            assert state["active_status"] == "transitioning"

@pytest.mark.asyncio
async def test_controller_state_synthesis():
    """Verify list_all_plugins synthesizes computed_status."""
    mock_container = MagicMock()
    mock_container.system_plugin_manager = None
    mock_container.mcp_host = None
    mock_container.heartbeat_service = None
    
    svc = PluginService(mock_container)
    
    # Scenario 1: Desired=True, Actual=Ready -> Running
    svc.plugin_registry = {
        "p1": {"id": "p1", "desired_enabled": True, "active_status": "ready", "worker_id": "w1"},
        "p2": {"id": "p2", "desired_enabled": True, "active_status": "loading", "worker_id": "w1"},
        "p3": {"id": "p3", "desired_enabled": False, "active_status": "ready", "worker_id": "w1"},
        "p4": {"id": "p4", "desired_enabled": True, "active_status": "unknown", "worker_id": "w1"},
    }
    
    # We need to mock get_lifecycle_bus for liveness check inside list_all_plugins
    mock_bus = AsyncMock()
    mock_bus.get_active_workers.return_value = [{"worker_id": "w1"}]
    
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=mock_bus):
        plugins = await svc.list_all_plugins()
        p_map = {p["id"]: p for p in plugins}
        
        assert p_map["p1"]["computed_status"] == "running"
        assert p_map["p2"]["computed_status"] == "provisioning"
        assert p_map["p3"]["computed_status"] == "stopping"
        assert p_map["p4"]["computed_status"] == "stuck"
        
        # UI Backwards Compat
        assert p_map["p1"]["enabled"] is True
        assert p_map["p3"]["enabled"] is False

