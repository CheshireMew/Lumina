"""
Unit tests for ServiceContainer
Tests dependency injection, service registration, and error handling
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.container import ServiceContainer, ServiceNotInitializedError, services


class TestServiceContainer(unittest.TestCase):
    def setUp(self):
        """Reset the singleton before each test"""
        # Clear the singleton instance
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    def test_singleton_pattern(self):
        """Verify that ServiceContainer follows singleton pattern"""
        instance1 = ServiceContainer.get_instance()
        instance2 = ServiceContainer.get_instance()
        self.assertIs(instance1, instance2)
        print("✅ Singleton pattern verified: same instance returned")

    def test_service_registration_and_retrieval(self):
        """Test basic service registration and retrieval"""
        mock_config = MagicMock()
        mock_config.test_attr = "test_value"

        self.container.set_config(mock_config)
        retrieved = self.container.get_config()

        self.assertIs(retrieved, mock_config)
        self.assertEqual(retrieved.test_attr, "test_value")
        print("✅ Service registration and retrieval working correctly")

    def test_uninitialized_service_raises_error(self):
        """Test that accessing uninitialized services raises proper error"""
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_gateway()
        self.assertIn("Gateway not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_soul()
        self.assertIn("SoulService not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_session_manager()
        self.assertIn("SessionManager not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_process_manager()
        self.assertIn("ProcessManager not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_worker_runtime_registry()
        self.assertIn("WorkerRuntimeRegistry not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_capability_registry()
        self.assertIn("CapabilityRegistry not initialized", str(cm.exception))
        with self.assertRaises(ServiceNotInitializedError) as cm:
            self.container.get_capability_module_manager()
        self.assertIn("CapabilityModuleManager not initialized", str(cm.exception))
        print("✅ Uninitialized service error handling verified")

    def test_multiple_service_registrations(self):
        """Test registering and retrieving multiple core services"""
        mock_event_bus = MagicMock(name="EventBus")
        mock_config = MagicMock(name="ConfigManager")
        mock_llm = MagicMock(name="LLMManager")

        self.container.set_event_bus(mock_event_bus)
        self.container.set_config(mock_config)
        self.container.set_llm_manager(mock_llm)

        self.assertIs(self.container.get_event_bus(), mock_event_bus)
        self.assertIs(self.container.get_config(), mock_config)
        self.assertIs(self.container.get_llm_manager(), mock_llm)
        print("✅ Multiple service registration verified")

    def test_explicit_gateway_access(self):
        """Test explicit gateway setter/getter access."""
        mock_gateway = MagicMock(name="Gateway")
        self.container.set_gateway(mock_gateway)

        self.assertIs(self.container.get_gateway(), mock_gateway)
        print("✅ Explicit gateway access verified")

    def test_context_provider_registry(self):
        """Test context provider registration and retrieval"""
        mock_provider1 = MagicMock(name="ContextProvider1")
        mock_provider1.id = "provider1"
        mock_provider2 = MagicMock(name="ContextProvider2")
        mock_provider2.id = "provider2"

        self.container.register_context_provider(mock_provider1)
        self.container.register_context_provider(mock_provider2)

        providers = self.container.get_context_providers()
        self.assertEqual(len(providers), 2)
        self.assertIn(mock_provider1, providers)
        self.assertIn(mock_provider2, providers)
        print("✅ Context provider registry verified")

    def test_tool_provider_registry(self):
        """Test tool provider registration and retrieval"""
        mock_tool = MagicMock(name="ToolProvider")
        mock_tool.name = "test_tool"

        self.container.register_tool_provider(mock_tool)
        retrieved = self.container.get_tool_provider("test_tool")

        self.assertIs(retrieved, mock_tool)

        # Test non-existent tool returns None
        none_result = self.container.get_tool_provider("non_existent")
        self.assertIsNone(none_result)
        print("✅ Tool provider registry verified")

    def test_search_provider_registry(self):
        """Test search provider registration and retrieval"""
        mock_search = MagicMock(name="SearchProvider")
        mock_search.id = "search1"

        self.container.register_search_provider(mock_search)
        retrieved = self.container.get_search_provider("search1")

        self.assertIs(retrieved, mock_search)
        print("✅ Search provider registry verified")

    def test_all_tools_retrieval(self):
        """Test retrieving all registered tools"""
        mock_tool1 = MagicMock(name="Tool1")
        mock_tool1.name = "tool1"
        mock_tool2 = MagicMock(name="Tool2")
        mock_tool2.name = "tool2"

        self.container.register_tool_provider(mock_tool1)
        self.container.register_tool_provider(mock_tool2)

        all_tools = self.container.get_all_tools()
        self.assertEqual(len(all_tools), 2)
        print("✅ All tools retrieval verified")

    def test_optional_service_returns_none(self):
        """Test that optional background services can return None"""
        result = self.container.get_ticker()
        self.assertIsNone(result)
        print("✅ Optional service handling verified")

    def test_global_services_singleton(self):
        """Test that the global 'services' instance works correctly"""
        mock_config = MagicMock(name="GlobalConfig")
        services.set_config(mock_config)

        self.assertIs(services.get_config(), mock_config)
        print("✅ Global services singleton verified")

    def test_setter_and_getter_consistency(self):
        """Test that setter and getter methods are consistent"""
        mock_vision = MagicMock(name="VisionService")
        mock_tts = MagicMock(name="TTSManager")
        mock_provider_config = MagicMock(name="ProviderConfigService")
        mock_context_resolver = MagicMock(name="CompanionContextResolver")
        mock_interaction_recorder = MagicMock(name="CompanionInteractionRecorder")
        mock_soul = MagicMock(name="SoulService")
        mock_session_manager = MagicMock(name="SessionManager")
        mock_process_manager = MagicMock(name="ProcessManager")
        mock_runtime_registry = MagicMock(name="WorkerRuntimeRegistry")
        mock_capability_registry = MagicMock(name="CapabilityRegistry")
        mock_capability_module_manager = MagicMock(name="CapabilityModuleManager")

        self.container.set_vision(mock_vision)
        self.container.set_tts(mock_tts)
        self.container.set_provider_config_service(mock_provider_config)
        self.container.set_companion_context_resolver(mock_context_resolver)
        self.container.set_companion_interaction_recorder(mock_interaction_recorder)
        self.container.set_soul(mock_soul)
        self.container.set_session_manager(mock_session_manager)
        self.container.set_process_manager(mock_process_manager)
        self.container.set_worker_runtime_registry(mock_runtime_registry)
        self.container.set_capability_registry(mock_capability_registry)
        self.container.set_capability_module_manager(mock_capability_module_manager)

        self.assertIs(self.container.get_vision(), mock_vision)
        self.assertIs(self.container.get_tts(), mock_tts)
        self.assertIs(self.container.get_provider_config_service(), mock_provider_config)
        self.assertIs(self.container.get_companion_context_resolver(), mock_context_resolver)
        self.assertIs(self.container.get_companion_interaction_recorder(), mock_interaction_recorder)
        self.assertIs(self.container.get_soul(), mock_soul)
        self.assertIs(self.container.get_session_manager(), mock_session_manager)
        self.assertIs(self.container.get_process_manager(), mock_process_manager)
        self.assertIs(self.container.get_worker_runtime_registry(), mock_runtime_registry)
        self.assertIs(self.container.get_capability_registry(), mock_capability_registry)
        self.assertIs(self.container.get_capability_module_manager(), mock_capability_module_manager)
        print("✅ Setter/getter consistency verified")


if __name__ == "__main__":
    # Run tests
    suite = unittest.TestLoader().loadTestsFromTestCase(TestServiceContainer)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # Print summary
    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All ServiceContainer tests passed!")
    print("="*60)
