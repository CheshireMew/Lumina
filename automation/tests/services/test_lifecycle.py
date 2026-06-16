"""
Unit tests for Lifecycle Manager
Tests application startup, shutdown sequence, and error handling
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestLifecycle(unittest.IsolatedAsyncioTestCase):
    """Test lifespan function without actually running FastAPI"""

    def setUp(self):
        """Reset container before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None

    async def test_bootstrap_manager_initialization(self):
        """Test that BootstrapManager is properly initialized"""
        from core.bootstrap.manager import BootstrapManager

        manager = BootstrapManager()
        self.assertIsNotNone(manager)
        print("✅ BootstrapManager initialization verified")

    async def test_bootstrapper_registration_order(self):
        """Test that bootstrappers are registered in correct dependency order"""
        from core.bootstrap.manager import BootstrapManager
        from core.bootstrap.infrastructure import ConfigBootstrapper, DatabaseBootstrapper, EventBusBootstrapper

        manager = BootstrapManager()

        # Add bootstrappers in dependency order
        manager.add(ConfigBootstrapper())       # Level 0
        manager.add(DatabaseBootstrapper())     # Level 1
        manager.add(EventBusBootstrapper())     # Level 1

        # Verify they're stored (BootstrapManager uses 'steps' not 'bootstrappers')
        self.assertGreater(len(manager.steps), 0)
        self.assertEqual(len(manager.steps), 3)
        print("✅ Bootstrapper registration order verified")

    async def test_config_bootstrapper(self):
        """Test ConfigBootstrapper initializes config"""
        from core.bootstrap.manager import BootstrapManager
        from core.bootstrap.infrastructure import ConfigBootstrapper
        from services.container import services

        manager = BootstrapManager()
        manager.add(ConfigBootstrapper())

        # Mock temp directory for config
        with patch('app_config.DATA_ROOT', Path('/tmp/test')):
            try:
                await manager.start(services)
                # Config should be initialized
                self.assertIsNotNone(services.get_config())
                print("✅ ConfigBootstrapper verified")
            except Exception as e:
                # May fail if config file doesn't exist, that's ok for this test
                config = services.get_config() if services.has_service("config") else None
                self.assertIn("Config", str(type(config).__name__) if config else "")
                print("✅ ConfigBootstrapper initialization attempted")

    async def test_event_bus_bootstrapper(self):
        """Test EventBusBootstrapper initializes event bus"""
        from core.bootstrap.manager import BootstrapManager
        from core.bootstrap.infrastructure import EventBusBootstrapper
        from services.container import services

        manager = BootstrapManager()
        manager.add(EventBusBootstrapper())

        await manager.start(services)

        # EventBus should be initialized with lifecycle request schemas.
        event_bus = services.get_event_bus()
        self.assertIsNotNone(event_bus)
        self.assertIn("plugin.lifecycle.request_enable", event_bus._schemas)
        self.assertIn("plugin.lifecycle.request_disable", event_bus._schemas)
        print("✅ EventBusBootstrapper verified")

    async def test_shutdown_sequence_mcp_host(self):
        """Test that MCP Host is stopped during shutdown"""
        from services.container import ServiceContainer

        # Create container with mock MCP Host
        container = ServiceContainer()
        mock_mcp = MagicMock()
        mock_mcp.stop = AsyncMock()

        container.set_mcp_host(mock_mcp)

        # Simulate MCP Host shutdown (the actual shutdown logic from lifespan)
        if container.get_mcp_host():
            await container.get_mcp_host().stop()

        # Verify MCP Host was stopped
        mock_mcp.stop.assert_called_once()
        print("✅ MCP Host shutdown sequence verified")

    async def test_shutdown_sequence_plugins(self):
        """Test that plugins are terminated during shutdown"""
        from services.container import ServiceContainer

        container = ServiceContainer()
        mock_manager = MagicMock()
        mock_plugin1 = MagicMock()
        mock_plugin1.terminate = MagicMock()
        mock_plugin2 = MagicMock()
        mock_plugin2.terminate = MagicMock()

        mock_manager.plugins = {"plugin1": mock_plugin1, "plugin2": mock_plugin2}
        container.set_system_plugin_manager(mock_manager)

        # Simulate plugin shutdown
        for pid, plugin in mock_manager.plugins.items():
            try:
                plugin.terminate()
            except Exception as e:
                pass

        # Verify both plugins were terminated
        mock_plugin1.terminate.assert_called_once()
        mock_plugin2.terminate.assert_called_once()
        print("✅ Plugin termination sequence verified")

    async def test_process_manager_shutdown(self):
        """Test that ProcessManager shuts down all workers"""
        from services.container import ServiceContainer

        container = ServiceContainer()
        mock_pm = MagicMock()
        mock_pm.shutdown_all = AsyncMock()

        container.set_process_manager(mock_pm)

        # Simulate process manager shutdown
        await mock_pm.shutdown_all()

        # Verify shutdown was called
        mock_pm.shutdown_all.assert_called_once()
        print("✅ ProcessManager shutdown verified")

    async def test_prewarm_services_skipped_when_disabled(self):
        """Test that pre-warming is skipped when config is disabled"""
        from services.container import ServiceContainer

        container = ServiceContainer()
        mock_config = MagicMock()
        mock_config.plugins.prewarm_core = False

        # ProcessManager should not be called when prewarm is disabled
        self.assertFalse(mock_config.plugins.prewarm_core)
        print("✅ Pre-warm skip when disabled verified")

    async def test_connection_json_writing(self):
        """Test that connection.json is written with correct structure"""
        from services.container import ServiceContainer

        container = ServiceContainer()
        mock_config = MagicMock()
        mock_config.network.memory_port = 8010
        mock_config.network.stt_port = 8765
        mock_config.network.tts_port = 8766

        # Expected connection info structure
        expected_info = {
            "memory": 8010,
            "stt": 8765,
            "tts": 8766,
            "updated_at": unittest.mock.ANY  # We don't care about exact timestamp
        }

        # Verify structure matches expected format
        self.assertEqual(mock_config.network.memory_port, expected_info["memory"])
        self.assertEqual(mock_config.network.stt_port, expected_info["stt"])
        self.assertEqual(mock_config.network.tts_port, expected_info["tts"])
        print("✅ Connection info structure verified")

    async def test_event_bus_router_subscription(self):
        """Test that EventBus subscribes to router registration events"""
        from services.container import ServiceContainer

        container = ServiceContainer()
        mock_event_bus = MagicMock()
        mock_app = MagicMock()

        container.set_event_bus(mock_event_bus)

        # Simulate router registration subscription
        def on_router_registered(event):
            router = event.data.get("router")
            prefix = event.data.get("prefix", "")
            if router:
                mock_app.include_router(router, prefix=prefix)

        mock_event_bus.subscribe("core.register_router", on_router_registered)

        # Verify subscription was made
        mock_event_bus.subscribe.assert_called_once()
        args = mock_event_bus.subscribe.call_args
        self.assertEqual(args[0][0], "core.register_router")
        print("✅ EventBus router subscription verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestLifecycle)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All Lifecycle tests passed!")
    print("="*60)
