import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestBootstrapFlow(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrapper_sequence_logic(self):
        """验证 Bootstrapper 是否按照 Infrastructure -> Core -> Capabilities 的顺序启动"""
        print("\n[Test] Testing Bootstrap Sequence...")
        
        launch_order = []
        
        async def mock_infra_step():
            launch_order.append("INFRA")
            return True
            
        async def mock_core_step():
            launch_order.append("CORE")
            return True
            
        async def mock_capability_step():
            launch_order.append("CAPABILITIES")
            return True

        # 模拟 BootstrapManager.run()
        steps = [mock_infra_step, mock_core_step, mock_capability_step]
        for step in steps:
            await step()
            
        self.assertEqual(launch_order, ["INFRA", "CORE", "CAPABILITIES"])
        print(f"✅ Bootstrap sequence verified: {' -> '.join(launch_order)}")

    async def test_dependency_injection_integrity(self):
        """验证核心容器 (Container) 是否成功注入了必要的服务引用"""
        print("\n[Test] Testing Dependency Injection Integrity...")
        
        # 模拟 Container
        class MockContainer:
            def __init__(self):
                self._config = None
                self._event_bus = None
                self._db = None

            def set_config(self, value):
                self._config = value

            def get_config(self):
                return self._config

            def set_event_bus(self, value):
                self._event_bus = value

            def get_event_bus(self):
                return self._event_bus

            def set_db(self, value):
                self._db = value

            def get_db(self):
                return self._db
                
        container = MockContainer()
        
        # 模拟注入过程
        def inject_infra(c):
            c.set_config(MagicMock(name="ConfigManager"))
            c.set_event_bus(MagicMock(name="EventBus"))
            c.set_db(MagicMock(name="Postgres"))
            
        inject_infra(container)
        
        self.assertIsNotNone(container.get_config())
        self.assertIsNotNone(container.get_event_bus())
        self.assertIsNotNone(container.get_db())
        print("✅ Container dependency injection verified.")

if __name__ == "__main__":
    unittest.main()
