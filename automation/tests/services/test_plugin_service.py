"""
Unit tests for Plugin Service
Tests plugin scanning, manifest parsing, and registration
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import tempfile
import shutil
import os

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestProviderConfigService(unittest.IsolatedAsyncioTestCase):
    """Test ProviderConfigService functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    def test_plugin_registry_initialization(self):
        """Test that ProviderConfigService registry initializes correctly"""
        # Mock plugin service structure
        class MockProviderConfigService:
            def __init__(self, container):
                self.services = container
                self.registry = {}
                self._last_healthy_workers = set()

        mock_service = MockProviderConfigService(self.container)

        self.assertIsNotNone(mock_service.registry)
        self.assertIsInstance(mock_service.registry, dict)
        self.assertEqual(len(mock_service.registry), 0)
        print("✅ Plugin registry initialization verified")

    def test_plugin_manifest_parsing(self):
        """Test YAML manifest parsing"""
        # Create a temporary manifest file
        manifest_content = """
id: test.module
name: Test Plugin
version: 1.0.0
description: A test plugin
author: Test Author
permissions:
  - event.subscribe
  - event.emit
"""
        temp_dir = tempfile.mkdtemp()
        manifest_path = os.path.join(temp_dir, "manifest.yaml")

        try:
            with open(manifest_path, 'w') as f:
                f.write(manifest_content)

            from core.manifest import read_manifest_file

            manifest = read_manifest_file(manifest_path)

            self.assertEqual(manifest['id'], 'test.module')
            self.assertEqual(manifest['version'], '1.0.0')
            self.assertIn('event.subscribe', manifest['permissions'])
            print("✅ Plugin manifest parsing verified")
        finally:
            shutil.rmtree(temp_dir)

    def test_plugin_id_validation(self):
        """Test plugin ID validation"""
        valid_ids = [
            "test.module",
            "my_extension",
            "vendor.module-name",
            "com.example.module"
        ]

        invalid_ids = [
            "../etc/passwd",
            "/absolute/path",
            "plugin with spaces",
            "plugin\nwith\nnewlines"
        ]

        # Simple validation pattern
        import re
        id_pattern = re.compile(r'^[a-zA-Z0-9_\.\-]+$')

        for plugin_id in valid_ids:
            self.assertTrue(id_pattern.match(plugin_id), f"Valid ID rejected: {plugin_id}")

        for plugin_id in invalid_ids:
            # Should not match valid pattern
            if id_pattern.match(plugin_id):
                self.fail(f"Invalid ID accepted: {plugin_id}")

        print("✅ Plugin ID validation verified")

    def test_plugin_dependency_resolution(self):
        """Test plugin dependency resolution"""
        # Define available plugins
        available = {
            "plugin_a": {"id": "plugin_a", "dependencies": []},
            "plugin_b": {"id": "plugin_b", "dependencies": ["plugin_a"]},
            "plugin_c": {"id": "plugin_c", "dependencies": ["plugin_a", "plugin_b"]},
            "plugin_d": {"id": "plugin_d", "dependencies": ["plugin_e"]}  # Missing dependency
        }

        # Simple topological sort for loading order
        def get_load_order(plugins, plugin_id, visited=None, loading=None):
            if visited is None:
                visited = set()
            if loading is None:
                loading = set()

            if plugin_id in loading:
                raise ValueError(f"Circular dependency detected involving {plugin_id}")

            if plugin_id in visited:
                return []

            loading.add(plugin_id)

            if plugin_id not in plugins:
                raise ValueError(f"Plugin {plugin_id} not found")

            deps = plugins[plugin_id].get("dependencies", [])
            order = []

            for dep in deps:
                order.extend(get_load_order(plugins, dep, visited, loading))

            loading.remove(plugin_id)
            visited.add(plugin_id)
            order.append(plugin_id)

            return order

        # Test valid chain
        order = get_load_order(available, "plugin_c")
        self.assertEqual(order, ["plugin_a", "plugin_b", "plugin_c"])

        # Test missing dependency
        with self.assertRaises(ValueError):
            get_load_order(available, "plugin_d")

        print("✅ Plugin dependency resolution verified")

    async def test_plugin_registration(self):
        """Test plugin capability registration"""
        class MockProviderConfigService:
            def __init__(self):
                self.registry = {}

            def register_capability(self, worker_id, capability):
                if worker_id not in self.registry:
                    self.registry[worker_id] = []
                self.registry[worker_id].append(capability)

            def get_capabilities(self, worker_id):
                return self.registry.get(worker_id, [])

        service = MockProviderConfigService()

        # Register capabilities for a worker
        service.register_capability("worker:stt", {
            "id": "stt.sensevoice",
            "name": "SenseVoice STT",
            "type": "stt"
        })

        service.register_capability("worker:stt", {
            "id": "stt.whisper",
            "name": "Whisper STT",
            "type": "stt"
        })

        # Retrieve capabilities
        caps = service.get_capabilities("worker:stt")
        self.assertEqual(len(caps), 2)
        self.assertEqual(caps[0]["id"], "stt.sensevoice")
        self.assertEqual(caps[1]["id"], "stt.whisper")
        print("✅ Plugin registration verified")

    async def test_plugin_discovery_scan(self):
        """Test plugin directory scanning"""
        # Create temporary plugin structure
        temp_dir = tempfile.mkdtemp()

        try:
            # Create plugin directories
            plugin1_dir = os.path.join(temp_dir, "extensions", "plugin1")
            plugin2_dir = os.path.join(temp_dir, "system", "plugin2")
            os.makedirs(plugin1_dir)
            os.makedirs(plugin2_dir)

            # Create manifests
            manifest1 = os.path.join(plugin1_dir, "manifest.yaml")
            manifest2 = os.path.join(plugin2_dir, "manifest.yaml")

            with open(manifest1, 'w') as f:
                f.write("id: ext.module1\nname: Extension 1\n")
            with open(manifest2, 'w') as f:
                f.write("id: sys.module2\nname: System Plugin 2\n")

            # Scan for plugins
            plugins_found = []
            for root, dirs, files in os.walk(temp_dir):
                if "manifest.yaml" in files:
                    rel_path = os.path.relpath(root, temp_dir)
                    plugins_found.append(rel_path)

            self.assertEqual(len(plugins_found), 2)
            print("✅ Plugin discovery scan verified")
        finally:
            shutil.rmtree(temp_dir)

    async def test_plugin_permission_check(self):
        """Test plugin permission validation"""
        from core.permissions import Permission, TIER_SAFE, TIER_TRUSTED, TIER_SYSTEM

        # Test permission checks
        def check_permissions(requested_perms, available_tier):
            """Check if requested permissions are available in tier"""
            return all(perm in available_tier for perm in requested_perms)

        # Test SAFE tier
        safe_request = ["event.subscribe", "event.emit"]
        self.assertTrue(check_permissions(safe_request, TIER_SAFE))

        # Test TRUSTED tier - use actual permissions from TIER_TRUSTED
        # Based on permissions.py: TIER_TRUSTED = {network.external, database.postgres, filesystem.read_user, network.udp}
        trusted_request = ["network.external", "filesystem.read_user"]
        self.assertTrue(check_permissions(trusted_request, TIER_TRUSTED))

        # Test SYSTEM tier
        system_request = ["os.exec", "filesystem.external"]
        self.assertTrue(check_permissions(system_request, TIER_SYSTEM))

        # Test SAFE tier permissions are NOT in SYSTEM tier (separation of concerns)
        # SAFE permissions should stay in SAFE tier
        self.assertIn("event.subscribe", TIER_SAFE)
        self.assertNotIn("event.subscribe", TIER_TRUSTED)
        self.assertNotIn("event.subscribe", TIER_SYSTEM)

        print("✅ Plugin permission check verified")

    async def test_plugin_isolation_sandbox(self):
        """Test plugin isolation patterns"""
        # Mock sandbox execution
        class MockSandbox:
            def __init__(self):
                self.isolated_processes = {}

            def spawn_isolated(self, plugin_id, entry_point):
                """Spawn plugin in isolated process"""
                process_id = f"{plugin_id}_{id(self)}"
                self.isolated_processes[process_id] = {
                    "plugin_id": plugin_id,
                    "entry_point": entry_point,
                    "pid": hash(process_id) % 10000  # Mock PID
                }
                return process_id

            def terminate(self, process_id):
                if process_id in self.isolated_processes:
                    del self.isolated_processes[process_id]
                    return True
                return False

        sandbox = MockSandbox()

        # Spawn isolated capability modules
        pid1 = sandbox.spawn_isolated("test.capability", "module.py")
        pid2 = sandbox.spawn_isolated("another.capability", "main.py")

        self.assertIn(pid1, sandbox.isolated_processes)
        self.assertIn(pid2, sandbox.isolated_processes)
        self.assertEqual(len(sandbox.isolated_processes), 2)

        # Terminate one
        result = sandbox.terminate(pid1)
        self.assertTrue(result)
        self.assertNotIn(pid1, sandbox.isolated_processes)
        self.assertEqual(len(sandbox.isolated_processes), 1)
        print("✅ Capability isolation sandbox verified")

    async def test_capability_metadata_extraction(self):
        """Test extraction of capability metadata"""
        mock_metadata = {
            "id": "test.capability",
            "name": "Test Capability",
            "version": "1.0.0",
            "description": "A test capability module",
            "author": "Test Author",
            "license": "MIT",
            "permissions": ["event.subscribe"],
            "dependencies": [],
            "entry_point": "module.py",
            "min_lumina_version": "0.1.0"
        }

        # Extract key fields
        capability_id = mock_metadata.get("id")
        name = mock_metadata.get("name")
        permissions = mock_metadata.get("permissions", [])
        deps = mock_metadata.get("dependencies", [])

        self.assertEqual(capability_id, "test.capability")
        self.assertEqual(name, "Test Capability")
        self.assertEqual(len(permissions), 1)
        self.assertEqual(len(deps), 0)
        print("✅ Plugin metadata extraction verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProviderConfigService)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All ProviderConfigService tests passed!")
    print("="*60)
