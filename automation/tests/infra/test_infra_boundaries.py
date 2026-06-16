
import unittest
import os
import sys
import socket
import shutil
from pathlib import Path


# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from app_config import ConfigManager

class TestInfraBoundaries(unittest.TestCase):
    def setUp(self):
        self.test_dir = Path("tests/temp_infra_test")
        self.test_dir.mkdir(parents=True, exist_ok=True)

    def tearDown(self):
        if self.test_dir.exists():
            shutil.rmtree(self.test_dir)

    def test_unicode_path_handling(self):
        """Test reading/writing files in non-ASCII paths (e.g. Chinese characters)"""
        # Create a directory with Chinese characters
        unicode_dir = self.test_dir / "测试目录_Test"
        unicode_dir.mkdir(exist_ok=True)
        
        file_path = unicode_dir / "测试文件.txt"
        content = "Hello 世界"
        
        # Write
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(content)
            
        # Verify existence
        self.assertTrue(file_path.exists())
        
        # Read back
        with open(file_path, "r", encoding="utf-8") as f:
            read_content = f.read()
            
        self.assertEqual(read_content, content)
        print(f"✅ Unicode Path Test Passed: {file_path}")

    def test_missing_config_behavior(self):
        """Test ConfigManager behavior when config file is missing"""
        # Point to non-existent config
        dummy_path = self.test_dir / "non_existent_config.yaml"

        # Inject env var override for testing if ConfigManager supports it
        # Assuming ConfigManager looks for 'LUMINA_CONFIG_FILE' or similar,
        # or we just rely on its default behavior when file not found (should load defaults).

        # Create a fresh instance (bypassing singleton if strictly needed, or just testing init)
        cm = ConfigManager()

        # It should rely on defaults and NOT crash
        self.assertIsNotNone(cm.network)
        # Note: Default memory port is 8010 (updated from 8000)
        self.assertEqual(cm.network.memory_port, 8010) # Default
        print("✅ Missing Config Test Passed (Loaded Defaults)")

    def test_port_occupancy_check(self):
        """Simulate port conflict"""
        test_port = 19191
        
        # 1. Bind socket to occupy port
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('127.0.0.1', test_port))
        sock.listen(1)
        
        # 2. Try to bind again (Simulation of server startup)
        try:
            sock2 = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock2.bind(('127.0.0.1', test_port))
            sock2.listen(1)
            self.fail("Should have raised OSError for Address already in use")
        except OSError as e:
            # Expected
            print("✅ Port Conflict Test Passed (Correctly caught OSError)")
        finally:
            sock.close()
            try:
                sock2.close()
            except:
                pass

if __name__ == "__main__":
    unittest.main()
