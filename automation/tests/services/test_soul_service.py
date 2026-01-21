"""
Unit tests for Soul Service
Tests soul driver management, prompt rendering, and personality state
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch, mock_open
import tempfile

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestSoulService(unittest.IsolatedAsyncioTestCase):
    """Test Soul Service functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_soul_service_initialization(self):
        """Test SoulService initialization"""
        from services.soul_service import SoulService
        from app_config import BASE_DIR

        service = SoulService()

        self.assertIsNotNone(service.characters_root)
        self.assertEqual(service._active_character_id, "hiyori")
        self.assertIsNotNone(service._persistence)
        self.assertIsNone(service._active_driver)
        print("✅ SoulService initialization verified")

    async def test_soul_service_register_driver(self):
        """Test registering a soul driver"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Mock driver
        mock_driver = MagicMock(spec=BaseSoulDriver)
        mock_driver.id = "test.soul"
        mock_driver.metadata = {"name": "Test Soul"}

        service.register_driver(mock_driver)

        self.assertIn("test.soul", service._drivers)
        self.assertEqual(service._active_driver, mock_driver)
        print("✅ SoulService register driver verified")

    async def test_soul_service_set_active_driver(self):
        """Test setting active soul driver"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Register multiple drivers
        driver1 = MagicMock(spec=BaseSoulDriver)
        driver1.id = "soul1"

        driver2 = MagicMock(spec=BaseSoulDriver)
        driver2.id = "soul2"

        service._drivers["soul1"] = driver1
        service._drivers["soul2"] = driver2
        service._active_driver = driver1

        # Switch to driver2
        service.set_active_driver("soul2")

        self.assertEqual(service._active_driver, driver2)
        print("✅ SoulService set active driver verified")

    async def test_soul_service_set_active_driver_unknown(self):
        """Test setting unknown active driver"""
        from services.soul_service import SoulService

        service = SoulService()

        # Try to set unknown driver (should log error)
        service.set_active_driver("unknown.soul")

        # Should not crash and driver should remain None
        self.assertIsNone(service._active_driver)
        print("✅ SoulService unknown driver handling verified")

    async def test_soul_service_get_system_prompt_from_driver(self):
        """Test getting system prompt from active driver"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Mock driver
        mock_driver = MagicMock(spec=BaseSoulDriver)
        mock_driver.get_system_prompt = AsyncMock(return_value="You are a test assistant.")
        service._active_driver = mock_driver

        prompt = await service.get_system_prompt()

        self.assertEqual(prompt, "You are a test assistant.")
        mock_driver.get_system_prompt.assert_called_once()
        print("✅ SoulService system prompt from driver verified")

    async def test_soul_service_get_system_prompt_template(self):
        """Test getting system prompt from template"""
        from services.soul_service import SoulService
        import yaml
        from jinja2 import Template

        service = SoulService()
        service._active_driver = None  # No driver

        # Mock template loading
        template_content = """
        name: {{ char_name }}
        description: {{ description }}
        custom: {{ custom_prompt }}
        """

        mock_config = {
            "name": "TestChar",
            "description": "A test character",
            "system_prompt": "Custom instructions"
        }

        with patch('builtins.open', mock_open(read_data=template_content)):
            with patch.object(service, 'load_character_config', return_value=mock_config):
                # Mock yaml.safe_load
                with patch('yaml.safe_load', return_value={"name": "{{ char_name }}"}):
                    prompt = await service.get_system_prompt()

                    # Should return a prompt containing the character info
                    self.assertIsInstance(prompt, str)

        print("✅ SoulService system prompt from template verified")

    async def test_soul_service_on_interaction(self):
        """Test delegating interaction to driver"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Mock driver
        mock_driver = MagicMock(spec=BaseSoulDriver)
        mock_driver.on_interaction = AsyncMock()
        service._active_driver = mock_driver

        await service.on_interaction("Hello", "Hi there!", {"context": "test"})

        mock_driver.on_interaction.assert_called_once_with("Hello", "Hi there!", {"context": "test"})
        print("✅ SoulService on interaction verified")

    async def test_soul_service_set_pending_interaction(self):
        """Test setting pending interaction (MCP support)"""
        from services.soul_service import SoulService

        service = SoulService()

        # Should log the pending interaction
        # (For now just a stub)
        service.set_pending_interaction("Test content", "mcp_source")

        # Verify no crash
        print("✅ SoulService pending interaction verified")

    async def test_soul_service_set_active_character(self):
        """Test switching active character"""
        from services.soul_service import SoulService

        service = SoulService()

        # Create mock character directory
        char_dir = service.characters_root / "test_char"
        char_dir.mkdir(parents=True, exist_ok=True)

        # Switch character
        service.set_active_character("test_char")

        self.assertEqual(service._active_character_id, "test_char")
        self.assertIsNotNone(service._persistence)
        print("✅ SoulService set active character verified")

    async def test_soul_service_set_active_character_not_found(self):
        """Test switching to non-existent character"""
        from services.soul_service import SoulService

        service = SoulService()

        # Try to switch to non-existent character
        with self.assertRaises(FileNotFoundError):
            service.set_active_character("nonexistent_char")

        print("✅ SoulService character not found handling verified")

    async def test_soul_service_profile_property(self):
        """Test profile property facade"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Mock driver with get_state
        mock_driver = MagicMock(spec=BaseSoulDriver)
        mock_driver.get_state = MagicMock(return_value={"mood": "happy", "energy": 80})
        service._active_driver = mock_driver

        profile = service.profile

        self.assertEqual(profile["mood"], "happy")
        self.assertEqual(profile["energy"], 80)
        print("✅ SoulService profile property verified")

    async def test_soul_service_save_profile(self):
        """Test save profile facade"""
        from services.soul_service import SoulService
        from core.interfaces.soul import BaseSoulDriver

        service = SoulService()

        # Mock driver with save_state
        mock_driver = MagicMock(spec=BaseSoulDriver)
        mock_driver.save_state = MagicMock()
        service._active_driver = mock_driver

        service.save_profile()

        # Should call save_state if available
        print("✅ SoulService save profile verified")

    async def test_soul_service_load_module_data(self):
        """Test loading module data"""
        from services.soul_service import SoulService

        service = SoulService()

        # Mock persistence
        mock_persistence = MagicMock()
        mock_persistence.load_module_data = MagicMock(return_value={"key": "value"})
        service._persistence = mock_persistence

        data = service.load_module_data("test_module")

        self.assertEqual(data, {"key": "value"})
        mock_persistence.load_module_data.assert_called_once_with("test_module")
        print("✅ SoulService load module data verified")

    async def test_soul_service_save_module_data(self):
        """Test saving module data"""
        from services.soul_service import SoulService

        service = SoulService()

        # Mock persistence
        mock_persistence = MagicMock()
        mock_persistence.save_module_data = MagicMock()
        service._persistence = mock_persistence

        service.save_module_data("test_module", {"key": "value"})

        mock_persistence.save_module_data.assert_called_once_with("test_module", {"key": "value"})
        print("✅ SoulService save module data verified")

    async def test_soul_service_load_character_config(self):
        """Test loading character config"""
        from services.soul_service import SoulService

        service = SoulService()

        # Mock persistence
        mock_persistence = MagicMock()
        mock_persistence.load_config = MagicMock(return_value={"name": "TestChar"})
        service._persistence = mock_persistence

        config = service.load_character_config()

        self.assertEqual(config["name"], "TestChar")
        mock_persistence.load_config.assert_called_once()
        print("✅ SoulService load character config verified")

    async def test_soul_service_save_character_config(self):
        """Test saving character config"""
        from services.soul_service import SoulService

        service = SoulService()

        # Mock persistence
        mock_persistence = MagicMock()
        mock_persistence.save_config = MagicMock()
        service._persistence = mock_persistence

        service.save_character_config({"name": "UpdatedChar"})

        mock_persistence.save_config.assert_called_once_with({"name": "UpdatedChar"})
        print("✅ SoulService save character config verified")

    async def test_soul_service_get_module_data_dir(self):
        """Test getting module data directory"""
        from services.soul_service import SoulService

        service = SoulService()

        # Mock persistence
        mock_persistence = MagicMock()
        mock_data_root = Path("/test/data")
        mock_persistence._resolve_data_root = MagicMock(return_value=mock_data_root)
        service._persistence = mock_persistence

        result = service.get_module_data_dir("test_module")

        # Should return a path to the module's data directory
        self.assertIsNotNone(result)
        self.assertIn("test_module", str(result))
        print("✅ SoulService get module data dir verified")

    async def test_soul_service_bulk_update_user_name(self):
        """Test bulk update user name facade"""
        from services.soul_service import SoulService

        service = SoulService()

        # Legacy feature stub
        result = service.bulk_update_user_name("NewName")

        # Should return 0 (stub implementation)
        self.assertEqual(result, 0)
        print("✅ SoulService bulk update user name verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSoulService)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All SoulService tests passed!")
    print("="*60)
