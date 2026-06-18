import sys
import asyncio
import logging
import pytest
from unittest.mock import MagicMock, AsyncMock

# Setup Path
from pathlib import Path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.events.bus import bus
from core.events.definitions import CapabilityLifecycleRequest
from services.capability_registry import CapabilityRegistry
from services.capability_module_manager import CapabilityModuleManager

# Mock Logger
logging.basicConfig(level=logging.INFO)

@pytest.mark.anyio
async def test_lifecycle_subscription():
    print("[Test] Setting up CapabilityModuleManager...")
    
    # 1. Mock Container & Dependencies
    mock_container = MagicMock()
    mock_container.has_service.return_value = True
    mock_container.get_event_bus.return_value = bus
    mock_container.get_capability_registry.return_value = CapabilityRegistry()
    mock_container.get_config.return_value = MagicMock()
    mock_container.get_worker_runtime_registry.return_value = MagicMock()
    
    # Instantiate
    manager = CapabilityModuleManager(container=mock_container)
    
    # 2. Mock Heavy Methods to isolate Event Logic
    manager.refresh_manifests = MagicMock() # Don't scan disk
    manager._emit_all_states = AsyncMock()
    
    # 3. Mock the Target Action
    # We want to verify _on_enable_request calls enable_module
    manager.enable_module = AsyncMock(return_value=True)
    manager.get_module = MagicMock(return_value=None)
    
    # 4. Start Manager (Triggers Subscription)
    await manager.start()
    
    # 5. Emit Event
    target_id = "test.module"
    print(f"[Test] Emitting request_enable for {target_id}...")
    
    req = CapabilityLifecycleRequest(module_id=target_id, requester="test_script")
    await bus.emit("capability.lifecycle.request_enable", req)
    
    # 6. Verify Outcome
    # Give the loop a moment to process the event
    await asyncio.sleep(0.1)
    
    if manager.enable_module.called:
        args = manager.enable_module.call_args
        assert args[0][0] == target_id
    else:
        pytest.fail("enable_module was not called. Subscription missing or broken.")

if __name__ == "__main__":
    try:
        asyncio.run(test_lifecycle_subscription())
    except Exception as e:
        print(f"❌ Test Error: {e}")
        raise
