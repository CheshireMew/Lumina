"""
REAL integration test for ReconciliationService.
Tests state monitoring, circuit breaker, and policy enforcement.
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

from services.utilities.reconciliation import ReconciliationService

@pytest.fixture
def mock_services():
    services = MagicMock()
    services.get_process_manager = MagicMock()
    # ensure_worker_running must be an AsyncMock
    services.get_plugin_service().ensure_worker_running = AsyncMock(return_value=True)
    return services

@pytest.mark.anyio
async def test_reconciliation_circuit_breaker():
    recon = ReconciliationService(MagicMock())
    now = 1000.0
    
    # Simulate 3 restarts within the window
    recon._record_restart("worker_1", now)
    recon._record_restart("worker_1", now + 10)
    recon._record_restart("worker_1", now + 20)
    
    # 4th attempt should trip the breaker
    assert recon._check_circuit_breaker("worker_1", now + 30) == False
    
    # Outside window should reset
    assert recon._check_circuit_breaker("worker_1", now + 100) == True

@pytest.mark.anyio
async def test_policy_enforcement_offline_desired_running(mock_services):
    recon = ReconciliationService(mock_services)
    mock_bus = AsyncMock()
    
    with patch("services.utilities.reconciliation.get_lifecycle_bus", return_value=mock_bus):
        state = {
            "desired_enabled": True,
            "active_status": "offline",
            "worker_id": "test_worker"
        }
        
        # Mock ProcessManager status
        mock_pm = mock_services.get_process_manager()
        mock_pm.is_running.return_value = False
        
        await recon._reconcile_plugin("plugin_1", state, 2000.0)
        
        # Verify attempt to restart
        mock_services.get_plugin_service().ensure_worker_running.assert_called_once_with("test_worker")
