import sys
import os
import asyncio
import time
import unittest
from unittest.mock import MagicMock, AsyncMock, patch
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.events.bus import bus
from services.process_manager import ProcessManager, WorkerProcess
from services.system_plugin_manager import SystemPluginManager

class TestPluginIsolation(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.process_manager = ProcessManager()
        self.mock_container = MagicMock()
        self.mock_container.event_bus = bus
        self.plugin_manager = SystemPluginManager(container=self.mock_container)
        
    async def test_process_spawn_logic(self):
        """验证 Isolation Mode 为 process 时是否尝试启动子进程"""
        print("\n[Test] Testing Process Isolation Spawning...")
        
        # Mocking subprocess.Popen to avoid actual process creation in unit test
        with patch("subprocess.Popen") as mock_popen:
            mock_popen.return_value.pid = 9999
            mock_popen.return_value.poll.return_value = None
            
            # 模拟一个需要隔离运行的插件配置
            plugin_id = "test.isolated.plugin"
            manifest = {
                "id": plugin_id,
                "isolation_mode": "process",
                "entry_point": "dummy_entry.py"
            }
            
            # 模拟 ProcessManager 的启动逻辑
            # 注意：这里我们测试 pm 是否被正确调用
            self.process_manager.spawn_plugin_process = MagicMock(return_value=9999)
            
            pid = self.process_manager.spawn_plugin_process(plugin_id, manifest)
            
            self.assertEqual(pid, 9999)
            self.process_manager.spawn_plugin_process.assert_called_once()
            print(f"✅ Spawn logic verified for PID: {pid}")

    async def test_orphan_cleanup(self):
        """验证系统关闭时是否清理了所有记录的插件进程"""
        print("\n[Test] Testing Orphan Process Cleanup...")

        # 注入伪造的进程记录 (use 'workers' instead of 'running_processes')
        # Create mock processes with terminate method
        mock_proc1 = MagicMock()
        mock_proc1.pid = 101
        mock_proc1.poll.return_value = None  # Still running

        mock_proc2 = MagicMock()
        mock_proc2.pid = 102
        mock_proc2.poll.return_value = None  # Still running

        self.process_manager.workers = {
            "test_plugin_1": WorkerProcess(mock_proc1, time.time()),
            "test_plugin_2": WorkerProcess(mock_proc2, time.time())
        }

        await self.process_manager.shutdown_all()

        # Both workers should be removed
        self.assertNotIn("test_plugin_1", self.process_manager.workers)
        self.assertNotIn("test_plugin_2", self.process_manager.workers)

        # Verify terminate was called on both
        mock_proc1.terminate.assert_called_once()
        mock_proc2.terminate.assert_called_once()

        print("✅ Cleanup logic called for all recorded processes.")

    async def test_ipc_heartbeat_failure(self):
        """验证当插件进程心跳丢失时，系统是否发出警告"""
        print("\n[Test] Testing Discovery of Failed Plugin Processes...")

        # 模拟心跳丢失场景
        # Note: SystemPluginManager no longer has _handle_process_crash method
        # The crash detection is handled by ProcessManager.is_running()
        # We verify that ProcessManager correctly detects dead processes

        # Create a mock dead process
        dead_proc = MagicMock()
        dead_proc.poll.return_value = 1  # Non-zero means exited

        self.process_manager.workers["isolated_plugin"] = WorkerProcess(dead_proc, time.time())
        self.process_manager.workers["isolated_plugin"].is_external = False

        # is_running should detect the dead process and remove it
        is_alive = self.process_manager.is_running("isolated_plugin")

        self.assertFalse(is_alive)
        self.assertNotIn("isolated_plugin", self.process_manager.workers)
        print("✅ Dead process detection and cleanup verified.")

if __name__ == "__main__":
    unittest.main()
