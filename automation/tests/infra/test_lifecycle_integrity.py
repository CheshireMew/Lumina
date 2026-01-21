import sys
import os
import asyncio
import logging
from unittest.mock import MagicMock, AsyncMock

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Setup Path
from pathlib import Path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.events.bus import bus
from core.events.definitions import PluginLifecycleRequest
from services.system_plugin_manager import SystemPluginManager

# Mock Logger
logging.basicConfig(level=logging.INFO)

async def test_lifecycle_subscription():
    print("[Test] Setting up SystemPluginManager...")
    
    # 1. Mock Container & Dependencies
    mock_container = MagicMock()
    mock_container.event_bus = bus
    
    # Instantiate
    manager = SystemPluginManager(container=mock_container)
    
    # 2. Mock Heavy Methods to isolate Event Logic
    manager._load_plugins = MagicMock() # Don't scan disk
    manager._distribute_plugins = AsyncMock() # Don't network
    manager._rebuild_index = MagicMock()
    manager.lifecycle_bus = MagicMock() # Don't talk to Surreal
    manager.audit_logger = MagicMock()
    
    # 3. Mock the Target Action
    # We want to verify _on_enable_request calls enable_plugin
    manager.enable_plugin = MagicMock(return_value=True)
    manager.get_plugin = MagicMock(return_value=None) # Simplify Config Update
    
    # 4. Start Manager (Triggers Subscription)
    await manager.start()
    
    # 5. Emit Event
    target_id = "test.plugin"
    print(f"[Test] Emitting request_enable for {target_id}...")
    
    req = PluginLifecycleRequest(plugin_id=target_id, requester="test_script")
    await bus.emit("plugin.lifecycle.request_enable", req)
    
    # 6. Verify Outcome
    # Give the loop a moment to process the event
    await asyncio.sleep(0.1)
    
    if manager.enable_plugin.called:
        args = manager.enable_plugin.call_args
        if args[0][0] == target_id:
             print("✅ PASSED: Manager received event and called enable_plugin.")
        else:
             print(f"❌ FAILED: enable_plugin called with wrong ID: {args[0][0]}")
             sys.exit(1)
    else:
        print("❌ FAILED: enable_plugin was NOT called. Subscription missing or broken.")
        sys.exit(1)

if __name__ == "__main__":
    try:
        asyncio.run(test_lifecycle_subscription())
    except Exception as e:
        print(f"❌ Test Error: {e}")
        sys.exit(1)
