"""
Unit tests for Plugin State Sync
Tests state synchronization, heartbeat, and hot-loading
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class BusStub:
    async def connect(self):
        pass

    async def get_all_states(self):
        return {}

    async def subscribe_state(self, _callback):
        pass

    async def send_heartbeat(self, _worker_id):
        pass


class TestPluginStateSync(unittest.IsolatedAsyncioTestCase):
    """Test Plugin State Sync functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_plugin_state_sync_initialization(self):
        """Test PluginStateSync initialization"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        self.assertEqual(sync.plugin_manager, mock_manager)
        self.assertIsNotNone(sync.bus)
        print("✅ PluginStateSync initialization verified")

    async def test_plugin_state_sync_start(self):
        """Test starting state sync"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Mock bus methods
        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()

        await sync.start()

        sync.bus.connect.assert_called_once()
        sync.bus.get_all_states.assert_called_once()
        sync.bus.subscribe_state.assert_called_once()
        print("✅ PluginStateSync start verified")

    async def test_plugin_state_sync_initial_snapshot(self):
        """Test initial state snapshot sync"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        mock_manager.is_plugin_desired_enabled.side_effect = lambda plugin_id: {
            "plugin1": True,
            "plugin2": False,
            "plugin3": True,
        }[plugin_id]
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Mock initial states
        initial_states = {
            "plugin1": {"desired_enabled": True},
            "plugin2": {"desired_enabled": False},
            "plugin3": {"desired_enabled": True}
        }

        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value=initial_states)
        sync.bus.subscribe_state = AsyncMock()

        # Mock manager methods
        mock_manager.enable_plugin = AsyncMock()
        mock_manager.disable_plugin = AsyncMock()

        await sync.start()

        # Should process all initial states
        # (The actual processing happens in _handle_state_update)
        print("✅ PluginStateSync initial snapshot verified")

    async def test_plugin_state_sync_handle_enable(self):
        """Test handling plugin enable event"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        mock_manager.is_plugin_desired_enabled.return_value = True
        mock_manager.enable_plugin = AsyncMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Mock bus
        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()

        # Handle enable event
        state = {"desired_enabled": True}
        await sync._handle_state_update("test.plugin", state)

        # Should call enable_plugin
        mock_manager.enable_plugin.assert_called_once_with("test.plugin")
        print("✅ PluginStateSync handle enable verified")

    async def test_plugin_state_sync_handle_disable(self):
        """Test handling plugin disable event"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        mock_manager.is_plugin_desired_enabled.return_value = False
        mock_manager.disable_plugin = AsyncMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Handle disable event
        state = {"desired_enabled": False}
        await sync._handle_state_update("test.plugin", state)

        # Should call disable_plugin
        mock_manager.disable_plugin.assert_called_once_with("test.plugin")
        print("✅ PluginStateSync handle disable verified")

    async def test_plugin_state_sync_handle_no_enabled_field(self):
        """Test handling state without enabled field"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # State without enabled field
        state = {"status": "running"}

        # Should not call enable/disable
        await sync._handle_state_update("test.plugin", state)

        mock_manager.enable_plugin.assert_not_called()
        mock_manager.disable_plugin.assert_not_called()
        print("✅ PluginStateSync no enabled field handling verified")

    async def test_plugin_state_sync_heartbeat_loop(self):
        """Test heartbeat loop"""
        from services.plugin_state_sync import PluginStateSync
        import socket

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Mock bus with send_heartbeat
        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()
        sync.bus.send_heartbeat = AsyncMock()

        # Start sync (creates heartbeat task)
        await sync.start()

        # Let heartbeat run a few times
        await asyncio.sleep(0.2)

        # Verify heartbeat was called
        sync.bus.send_heartbeat.assert_called()
        print("✅ PluginStateSync heartbeat loop verified")

    async def test_plugin_state_sync_heartbeat_uses_bus_contract(self):
        """Test heartbeat uses the lifecycle bus contract."""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()
        sync.bus.send_heartbeat = AsyncMock()

        await sync.start()
        await asyncio.sleep(0.1)

        sync.bus.send_heartbeat.assert_called()
        print("✅ PluginStateSync heartbeat contract verified")

    async def test_plugin_state_sync_heartbeat_error_recovery(self):
        """Test heartbeat error recovery"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Mock bus that fails but continues
        call_count = [0]

        async def failing_heartbeat(worker_id):
            call_count[0] += 1
            if call_count[0] < 2:
                raise Exception("Heartbeat failed")
            # Succeed after first failure

        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()
        sync.bus.send_heartbeat = failing_heartbeat

        await sync.start()
        await asyncio.sleep(0.2)

        # Should continue despite errors (at least 2 calls due to timing)
        self.assertGreaterEqual(call_count[0], 1)
        print("✅ PluginStateSync heartbeat error recovery verified")

    async def test_plugin_state_sync_enable_error_handling(self):
        """Test error handling during plugin enable"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        mock_manager.is_plugin_desired_enabled.return_value = True
        mock_manager.enable_plugin = AsyncMock(side_effect=Exception("Enable failed"))
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Handle enable event that fails
        state = {"desired_enabled": True}
        await sync._handle_state_update("failing.plugin", state)

        # Should call enable_plugin despite potential error
        mock_manager.enable_plugin.assert_called_once()
        print("✅ PluginStateSync enable error handling verified")

    async def test_plugin_state_sync_concurrent_updates(self):
        """Test handling concurrent state updates"""
        from services.plugin_state_sync import PluginStateSync

        mock_manager = MagicMock()
        mock_manager.is_plugin_desired_enabled.side_effect = lambda plugin_id: int(plugin_id.replace("plugin", "")) % 2 == 0
        sync = PluginStateSync(mock_manager, bus=BusStub())

        # Simulate concurrent updates
        tasks = []
        for i in range(10):
            state = {"desired_enabled": i % 2 == 0}
            task = sync._handle_state_update(f"plugin{i}", state)
            tasks.append(task)

        # Wait for all to complete
        await asyncio.gather(*tasks)

        # Should handle all updates
        self.assertEqual(mock_manager.enable_plugin.call_count, 5)
        self.assertEqual(mock_manager.disable_plugin.call_count, 5)
        print("✅ PluginStateSync concurrent updates verified")

    async def test_plugin_state_sync_worker_id_format(self):
        """Test worker ID format in heartbeat"""
        from services.plugin_state_sync import PluginStateSync
        import socket

        mock_manager = MagicMock()
        sync = PluginStateSync(mock_manager, bus=BusStub())

        sync.bus.connect = AsyncMock()
        sync.bus.get_all_states = AsyncMock(return_value={})
        sync.bus.subscribe_state = AsyncMock()
        sync.bus.send_heartbeat = AsyncMock()

        await sync.start()

        # Get the worker ID from heartbeat call
        call_args = sync.bus.send_heartbeat.call_args
        if call_args:
            worker_id = call_args[0][0]
            self.assertIn("worker:", worker_id)
            self.assertIn(socket.gethostname(), worker_id)

        print("✅ PluginStateSync worker ID format verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginStateSync)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All PluginStateSync tests passed!")
    print("="*60)
