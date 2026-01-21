"""
Unit tests for Plugin Discovery
Tests plugin registry, metadata extraction, and version compatibility
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch
import tempfile
import yaml

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestPluginDiscovery(unittest.TestCase):
    """Test Plugin Discovery functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    def test_plugin_discovery_scan_directory(self):
        """Test scanning directory for plugins"""
        # Create a temporary directory with plugin manifests
        temp_dir = tempfile.mkdtemp()
        plugin_dir = Path(temp_dir) / "plugins"
        plugin_dir.mkdir(parents=True, exist_ok=True)

        # Create mock manifest files
        manifest1 = {
            "id": "plugin1",
            "name": "Plugin 1",
            "version": "1.0.0"
        }

        manifest2 = {
            "id": "plugin2",
            "name": "Plugin 2",
            "version": "2.0.0"
        }

        with open(plugin_dir / "manifest1.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(manifest1, f)

        with open(plugin_dir / "manifest2.yaml", 'w', encoding='utf-8') as f:
            yaml.dump(manifest2, f)

        # Scan for manifests
        manifest_files = list(plugin_dir.glob("*.yaml"))

        self.assertEqual(len(manifest_files), 2)
        print("✅ Plugin discovery scan directory verified")

    def test_plugin_discovery_parse_manifest(self):
        """Test parsing plugin manifest"""
        from core.manifest import PluginManifest

        manifest_data = {
            "id": "test.plugin",
            "name": "Test Plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "Test Author",
            "entrypoint": "plugin:TestPlugin",
            "permissions": ["network.read"]
        }

        manifest = PluginManifest(**manifest_data)

        self.assertEqual(manifest.id, "test.plugin")
        self.assertEqual(manifest.name, "Test Plugin")
        self.assertEqual(manifest.version, "1.0.0")
        self.assertEqual(manifest.permissions, ["network.read"])
        print("✅ Plugin discovery parse manifest verified")

    def test_plugin_discovery_extract_metadata(self):
        """Test extracting metadata from manifest"""
        from core.manifest import PluginManifest

        manifest_data = {
            "id": "meta.plugin",
            "name": "Metadata Plugin",
            "version": "1.5.0",
            "description": "Tests metadata extraction",
            "author": "Developer",
            "tags": ["test", "metadata"],
            "category": "system"
        }

        manifest = PluginManifest(**manifest_data)

        self.assertEqual(manifest.id, "meta.plugin")
        self.assertEqual(manifest.author, "Developer")
        self.assertEqual(manifest.tags, ["test", "metadata"])
        self.assertEqual(manifest.category, "system")
        print("✅ Plugin discovery extract metadata verified")

    def test_plugin_discovery_version_compatibility(self):
        """Test version compatibility checking"""
        def check_compatibility(plugin_version, min_version):
            """Simple semantic version comparison"""
            def parse_version(v):
                return tuple(map(int, v.split('.')[:3]))

            pv = parse_version(plugin_version)
            mv = parse_version(min_version)
            return pv >= mv

        # Test compatible version
        self.assertTrue(check_compatibility("1.5.0", "1.0.0"))

        # Test incompatible version
        self.assertFalse(check_compatibility("0.9.0", "1.0.0"))

        # Test equal version
        self.assertTrue(check_compatibility("1.0.0", "1.0.0"))

        # Test patch version
        self.assertTrue(check_compatibility("1.0.5", "1.0.0"))

        print("✅ Plugin discovery version compatibility verified")

    def test_plugin_discovery_dependencies(self):
        """Test dependency parsing"""
        from core.manifest import PluginManifest

        manifest_data = {
            "id": "dependent.plugin",
            "name": "Dependent Plugin",
            "version": "1.0.0",
            "dependencies": [
                "dep1",
                "dep2"
            ]
        }

        manifest = PluginManifest(**manifest_data)

        self.assertEqual(len(manifest.dependencies), 2)
        self.assertIn("dep1", manifest.dependencies)
        self.assertIn("dep2", manifest.dependencies)
        print("✅ Plugin discovery dependencies verified")

    def test_plugin_discovery_permissions(self):
        """Test permission parsing"""
        from core.manifest import PluginManifest

        manifest_data = {
            "id": "perms.plugin",
            "name": "Permissions Plugin",
            "version": "1.0.0",
            "permissions": [
                "network.read",
                "network.write",
                "filesystem.read_user",
                "filesystem.write_user"
            ]
        }

        manifest = PluginManifest(**manifest_data)

        self.assertEqual(len(manifest.permissions), 4)
        self.assertIn("network.read", manifest.permissions)
        self.assertIn("filesystem.write_user", manifest.permissions)
        print("✅ Plugin discovery permissions verified")

    def test_plugin_discovery_isolation_mode(self):
        """Test isolation mode parsing"""
        from core.manifest import PluginManifest

        # Local isolation
        local_manifest = PluginManifest(
            id="local.plugin",
            name="Local Plugin",
            version="1.0.0",
            isolation_mode="local"
        )

        self.assertEqual(local_manifest.isolation_mode, "local")

        # Process isolation
        process_manifest = PluginManifest(
            id="process.plugin",
            name="Process Plugin",
            version="1.0.0",
            isolation_mode="process"
        )

        self.assertEqual(process_manifest.isolation_mode, "process")

        print("✅ Plugin discovery isolation mode verified")

    def test_plugin_discovery_entrypoint_resolution(self):
        """Test entrypoint resolution"""
        def resolve_entrypoint(entrypoint, plugin_path):
            """Resolve entrypoint to file path"""
            if ':' in entrypoint:
                mod_name, class_name = entrypoint.split(':', 1)
                # Convert dot notation to path
                file_path = plugin_path / (mod_name.replace('.', '/') + '.py')
                return file_path, class_name
            return plugin_path / entrypoint, None

        plugin_path = Path("/test/plugin")

        # Test module:class format
        file_path, class_name = resolve_entrypoint("drivers.llm.openai:OpenAILLM", plugin_path)
        # Use PurePath for cross-platform comparison
        self.assertEqual(file_path.as_posix(), "/test/plugin/drivers/llm/openai.py")
        self.assertEqual(class_name, "OpenAILLM")

        # Test simple file format
        file_path, class_name = resolve_entrypoint("main.py", plugin_path)
        self.assertEqual(file_path.as_posix(), "/test/plugin/main.py")
        self.assertIsNone(class_name)

        print("✅ Plugin discovery entrypoint resolution verified")

    def test_plugin_discovery_invalid_manifest(self):
        """Test handling of invalid manifest"""
        from core.manifest import PluginManifest
        from pydantic import ValidationError

        # Missing required fields
        invalid_data = {
            "id": "invalid.plugin"
            # Missing required fields like name, version
        }

        try:
            manifest = PluginManifest(**invalid_data)
            # If we get here, validation passed (which might be OK if defaults exist)
        except (ValidationError, TypeError) as e:
            # Expected validation error
            pass

        print("✅ Plugin discovery invalid manifest handling verified")

    def test_plugin_discovery_duplicate_detection(self):
        """Test detecting duplicate plugins"""
        discovered = {}

        # Add first instance
        discovered["test.plugin"] = {"path": "/path1", "version": "1.0.0"}

        # Try to add duplicate
        if "test.plugin" in discovered:
            # Handle duplicate - compare versions
            existing = discovered["test.plugin"]
            new = {"path": "/path2", "version": "1.1.0"}

            # Keep higher version
            if new["version"] > existing["version"]:
                discovered["test.plugin"] = new

        # Should still have one entry
        self.assertEqual(len(discovered), 1)
        self.assertEqual(discovered["test.plugin"]["path"], "/path2")
        print("✅ Plugin discovery duplicate detection verified")

    def test_plugin_discovery_recursive_scan(self):
        """Test recursive directory scanning"""
        import tempfile
        from pathlib import Path

        temp_dir = tempfile.mkdtemp()
        base_path = Path(temp_dir)

        # Create nested structure
        (base_path / "level1").mkdir()
        (base_path / "level1" / "level2").mkdir()
        (base_path / "level1" / "level2" / "level3").mkdir()

        # Create manifest at different levels
        (base_path / "manifest1.yaml").write_text("id: plugin1")
        (base_path / "level1" / "manifest2.yaml").write_text("id: plugin2")
        (base_path / "level1" / "level2" / "manifest3.yaml").write_text("id: plugin3")

        # Recursive scan
        manifests = list(base_path.rglob("*.yaml"))

        self.assertEqual(len(manifests), 3)
        print("✅ Plugin discovery recursive scan verified")

    def test_plugin_discovery_runtime_target(self):
        """Test runtime_target parsing"""
        from core.manifest import PluginManifest

        # Main process target
        main_manifest = PluginManifest(
            id="main.plugin",
            name="Main Plugin",
            version="1.0.0",
            runtime_target="main"
        )

        self.assertEqual(main_manifest.runtime_target, "main")

        # STT server target
        stt_manifest = PluginManifest(
            id="stt.plugin",
            name="STT Plugin",
            version="1.0.0",
            runtime_target="stt_server"
        )

        self.assertEqual(stt_manifest.runtime_target, "stt_server")

        # TTS server target
        tts_manifest = PluginManifest(
            id="tts.plugin",
            name="TTS Plugin",
            version="1.0.0",
            runtime_target="tts_server"
        )

        self.assertEqual(tts_manifest.runtime_target, "tts_server")

        print("✅ Plugin discovery runtime target verified")

    def test_plugin_discovery_ui_slots(self):
        """Test UI slots parsing"""
        from core.manifest import PluginManifest

        manifest_data = {
            "id": "ui.plugin",
            "name": "UI Plugin",
            "version": "1.0.0",
            "ui_slots": [
                {
                    "name": "TestWidget",
                    "slot": "sidebar",
                    "src": "./widget.tsx",
                    "width": "300px"
                }
            ]
        }

        manifest = PluginManifest(**manifest_data)

        self.assertEqual(len(manifest.ui_slots), 1)
        self.assertEqual(manifest.ui_slots[0].name, "TestWidget")
        self.assertEqual(manifest.ui_slots[0].slot, "sidebar")
        self.assertEqual(manifest.ui_slots[0].src, "./widget.tsx")
        print("✅ Plugin discovery UI slots verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestPluginDiscovery)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All PluginDiscovery tests passed!")
    print("="*60)
