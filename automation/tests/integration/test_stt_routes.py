
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from unittest.mock import MagicMock, AsyncMock, patch

# Adjust path to include python_backend
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "../../../python_backend")))

try:
    stt_routes = pytest.importorskip("capabilities.stt.routes")
except RuntimeError as exc:
    if "python-multipart" in str(exc):
        pytest.skip("python-multipart is required for STT route integration tests", allow_module_level=True)
    raise
from routers.deps import get_stt_service

app = FastAPI()
app.include_router(stt_routes.router)
client = TestClient(app)

@pytest.fixture
def mock_stt_manager():
    manager = MagicMock()
    manager.has_driver.return_value = True
    manager.active_driver_id = "mock_driver"
    manager.switch_model_background = AsyncMock()
    return manager

def test_switch_model_signature(mock_stt_manager):
    """
    [Phase 7] Integration Test for Switch Endpoint.
    Verifies that 'switch_model' correctly accepts JSON payload AND Request object.
    Regression test for: 'request' parameter masking FastAPI Request.
    """
    
    # 1. Override Dependency
    app.dependency_overrides[get_stt_service] = lambda: mock_stt_manager
    
    # 2. Mock App State Reporter (for logic test)
    mock_reporter = AsyncMock()
    app.state.reporter = mock_reporter
    
    # 3. Payload
    payload = {"model_name": "mock_driver"}
    
    # 4. Action
    response = client.post("/models/switch", json=payload)
    
    # 5. Verify
    assert response.status_code == 200, f"Expected 200, got {response.status_code}: {response.text}"
    assert response.json()["active_model"] == "mock_driver"
    
    # Verify Manager Call
    mock_stt_manager.switch_model_background.assert_called_with("mock_driver")
    
    # Verify Force Report (The extra logic ensuring Request was injected correctly)
    mock_reporter.force_report.assert_called_once()
    
    # Cleanup
    app.dependency_overrides = {}

def test_switch_model_validation_error(mock_stt_manager):
    """Verify 422 for missing body."""
    app.dependency_overrides[get_stt_service] = lambda: mock_stt_manager
    response = client.post("/models/switch", json={}) # Missing model_name
    assert response.status_code == 422
    app.dependency_overrides = {}
