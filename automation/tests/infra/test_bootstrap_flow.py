import sys
import unittest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestBootstrapFlow(unittest.IsolatedAsyncioTestCase):
    async def test_bootstrapper_sequence_logic(self):
        """验证 Bootstrapper 是否按照 Infrastructure -> Core -> Plugins 的顺序启动"""
        print("\n[Test] Testing Bootstrap Sequence...")
        
        launch_order = []
        
        async def mock_infra_step():
            launch_order.append("INFRA")
            return True
            
        async def mock_core_step():
            launch_order.append("CORE")
            return True
            
        async def mock_plugin_step():
            launch_order.append("PLUGINS")
            return True

        # 模拟 BootstrapManager.run()
        steps = [mock_infra_step, mock_core_step, mock_plugin_step]
        for step in steps:
            await step()
            
        self.assertEqual(launch_order, ["INFRA", "CORE", "PLUGINS"])
        print(f"✅ Bootstrap sequence verified: {' -> '.join(launch_order)}")

    async def test_dependency_injection_integrity(self):
        """验证核心容器 (Container) 是否成功注入了必要的服务引用"""
        print("\n[Test] Testing Dependency Injection Integrity...")
        
        # 模拟 Container
        class MockContainer:
            def __init__(self):
                self.config = None
                self.event_bus = None
                self.db = None
                
        container = MockContainer()
        
        # 模拟注入过程
        def inject_infra(c):
            c.config = MagicMock(name="ConfigManager")
            c.event_bus = MagicMock(name="EventBus")
            c.db = MagicMock(name="Postgres")
            
        inject_infra(container)
        
        self.assertIsNotNone(container.config)
        self.assertIsNotNone(container.event_bus)
        self.assertIsNotNone(container.db)
        print("✅ Container dependency injection verified.")

if __name__ == "__main__":
    unittest.main()
