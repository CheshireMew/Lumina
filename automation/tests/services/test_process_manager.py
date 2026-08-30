"""
Unit tests for Process Manager
Tests worker process lifecycle, crash recovery, and resource cleanup
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import subprocess
import time

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class EmptyWorkerRuntimeRegistry:
    def runtime_for_capability(self, capability: str):
        return None

    def should_auto_start(self, capability: str) -> bool:
        return False


def build_process_manager():
    from services.process_manager import ProcessManager

    return ProcessManager(EmptyWorkerRuntimeRegistry())


class TestProcessManager(unittest.TestCase):
    """Test Process Manager functionality"""

    def setUp(self):
        from services.container import ServiceContainer
        self.container = ServiceContainer()

    def test_process_manager_initialization(self):
        """Test ProcessManager initialization"""
        manager = build_process_manager()

        self.assertIsNotNone(manager.workers)
        self.assertIsNotNone(manager.registry)
        self.assertIsInstance(manager.workers, dict)
        self.assertIsInstance(manager.registry, dict)
        print("✅ ProcessManager initialization verified")

    def test_process_manager_requires_runtime_registry(self):
        """Test ProcessManager refuses half-initialized runtime dependencies"""
        from services.process_manager import ProcessManager

        with self.assertRaises(ValueError):
            ProcessManager(None)
        print("✅ ProcessManager runtime registry requirement verified")

    def test_process_manager_register_service_def(self):
        """Test registering a service definition"""
        manager = build_process_manager()
        manager.register_service_def("test_service", port=8080, script="test.py", args=["--verbose"])

        self.assertIn("test_service", manager.registry)
        self.assertEqual(manager.registry["test_service"]["port"], 8080)
        self.assertEqual(manager.registry["test_service"]["script"], "test.py")
        self.assertEqual(manager.registry["test_service"]["args"], ["--verbose"])
        print("✅ ProcessManager register service definition verified")

    def test_process_manager_set_health_path(self):
        """Test setting custom health path"""
        manager = build_process_manager()
        manager.register_service_def("test_service", port=8080)
        manager.set_health_path("test_service", "/custom/health")

        self.assertEqual(manager.registry["test_service"]["health_path"], "/custom/health")
        print("✅ ProcessManager set health path verified")

    def test_process_manager_check_port_open(self):
        """Test port availability check"""
        from services.health_probe import HealthProbe

        # Test with likely closed port
        result = HealthProbe().is_port_open(59999)  # Unlikely to be in use

        # Should return False for closed port
        self.assertFalse(result)
        print("✅ ProcessManager check port open verified")

    def test_process_manager_check_http_health(self):
        """Test HTTP health check"""
        from services.health_probe import HealthProbe

        # Test with non-existent service
        result = HealthProbe().is_http_healthy(59999, "/health")

        # Should return False when no service running
        self.assertFalse(result)
        print("✅ ProcessManager check HTTP health verified")

    def test_process_manager_is_running_not_found(self):
        """Test is_running for non-existent worker"""
        manager = build_process_manager()

        result = manager.is_running("nonexistent_worker")

        self.assertFalse(result)
        print("✅ ProcessManager is_running not found verified")

    def test_process_manager_worker_process(self):
        """Test WorkerProcess object"""
        from services.process_manager import WorkerProcess

        # Mock process
        mock_process = MagicMock()
        mock_process.pid = 12345

        worker = WorkerProcess(mock_process, time.time())

        self.assertEqual(worker.process, mock_process)
        self.assertIsNotNone(worker.start_time)
        self.assertIsNotNone(worker.last_heartbeat)
        self.assertFalse(worker.is_external)
        print("✅ ProcessManager WorkerProcess verified")

    def test_process_manager_stop_worker_not_found(self):
        """Test stopping non-existent worker"""
        manager = build_process_manager()

        # Should not crash
        asyncio.run(manager.stop_worker("nonexistent_worker"))

        self.assertNotIn("nonexistent_worker", manager.workers)
        print("✅ ProcessManager stop worker not found verified")

    def test_process_manager_stop_external_worker(self):
        """Test stopping external worker (should only log warning)"""
        from services.process_manager import WorkerProcess

        manager = build_process_manager()

        # Create external worker
        external_worker = WorkerProcess(None, time.time())
        external_worker.is_external = True
        manager.workers["external_service"] = external_worker

        # Stop should only remove from tracking, not try to kill
        asyncio.run(manager.stop_worker("external_service"))

        self.assertNotIn("external_service", manager.workers)
        print("✅ ProcessManager stop external worker verified")

    def test_process_manager_get_active_workers(self):
        """Test getting active workers list"""
        from services.process_manager import WorkerProcess

        manager = build_process_manager()

        # Add some workers
        mock_proc = MagicMock()
        worker1 = WorkerProcess(mock_proc, time.time())
        manager.workers["worker1"] = worker1

        # Mock is_running to return True
        manager.is_running = MagicMock(return_value=True)

        active = manager.get_active_workers()

        self.assertIn("worker1", active)
        print("✅ ProcessManager get active workers verified")

    def test_process_manager_shutdown_all(self):
        """Test shutting down all workers"""
        async def run_test():
            from services.process_manager import WorkerProcess

            manager = build_process_manager()

            # Add some mock workers
            mock_proc1 = MagicMock()
            mock_proc1.terminate = MagicMock()
            mock_proc1.wait = MagicMock(return_value=0)
            worker1 = WorkerProcess(mock_proc1, time.time())

            mock_proc2 = MagicMock()
            mock_proc2.terminate = MagicMock()
            mock_proc2.wait = MagicMock(return_value=0)
            worker2 = WorkerProcess(mock_proc2, time.time())

            manager.workers["worker1"] = worker1
            manager.workers["worker2"] = worker2

            await manager.shutdown_all()

            # Both workers should be stopped and removed
            self.assertNotIn("worker1", manager.workers)
            self.assertNotIn("worker2", manager.workers)
            print("✅ ProcessManager shutdown all verified")

        asyncio.run(run_test())

    def test_process_manager_start_worker_already_running(self):
        """Test starting worker that's already running"""
        from services.process_manager import WorkerProcess

        manager = build_process_manager()

        # Add existing worker
        mock_proc = MagicMock()
        mock_proc.poll = MagicMock(return_value=None)  # Still running
        worker = WorkerProcess(mock_proc, time.time())
        manager.workers["test_worker"] = worker

        # Mock is_running to return True
        manager.is_running = MagicMock(return_value=True)

        result = manager.start_worker("test_worker")

        self.assertTrue(result)
        # Should not spawn new process
        print("✅ ProcessManager start worker already running verified")

    def test_process_manager_start_worker_no_registry(self):
        """Test starting worker without registry entry"""
        manager = build_process_manager()

        # No registry entry and no script provided
        result = manager.start_worker("no_registry_worker")

        self.assertFalse(result)
        print("✅ ProcessManager start worker no registry verified")

    def test_process_manager_external_service_detection(self):
        """Test detection of externally running service"""
        manager = build_process_manager()
        manager.register_service_def("external_test", port=59999, script="missing.py")

        # Mock health check to return False (service not running)
        with patch(
            'services.health_probe.HealthProbe.is_service_reachable',
            return_value=(False, "none"),
        ):
            result = manager.start_worker("external_test")

        self.assertFalse(result)
        self.assertNotIn("external_test", manager.workers)
        print("✅ ProcessManager external service detection verified")

    def test_process_manager_terminate_timeout(self):
        """Test process-tree kill after graceful shutdown timeout"""
        from services.process_manager import WorkerProcess
        import subprocess

        manager = build_process_manager()

        # Mock process that times out on terminate
        mock_proc = MagicMock()
        mock_proc.pid = 12345
        mock_proc.terminate = MagicMock()
        mock_proc.wait = MagicMock(side_effect=subprocess.TimeoutExpired("cmd", 5))
        mock_proc.kill = MagicMock()

        worker = WorkerProcess(mock_proc, time.time())
        manager.workers["timeout_worker"] = worker

        with patch("services.process_manager.subprocess.run") as taskkill:
            asyncio.run(manager.stop_worker("timeout_worker"))

        mock_proc.terminate.assert_called_once_with()
        mock_proc.kill.assert_not_called()
        taskkill.assert_called_once_with(
            ["taskkill", "/PID", "12345", "/T", "/F"],
            check=False,
            capture_output=True,
        )
        print("✅ ProcessManager terminate timeout verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestProcessManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All ProcessManager tests passed!")
    print("="*60)
