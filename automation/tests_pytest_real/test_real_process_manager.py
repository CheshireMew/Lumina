import time
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest

from services.process_manager import ProcessManager
from services.worker_supervisor import RestartPolicy, WorkerProcess


class FakeProcess:
    def __init__(self, pid: int = 12345, returncode=None):
        self.pid = pid
        self.returncode = returncode
        self.terminated = False
        self.killed = False

    def poll(self):
        return self.returncode

    def terminate(self):
        self.terminated = True

    def wait(self, timeout=None):
        return self.returncode or 0

    def kill(self):
        self.killed = True


class EmptyWorkerRuntimeRegistry:
    def runtime_for_capability(self, capability: str):
        return None

    def should_auto_start(self, capability: str) -> bool:
        return False


def build_process_manager():
    return ProcessManager(EmptyWorkerRuntimeRegistry())


def test_process_manager_initializes_current_components():
    manager = build_process_manager()

    assert manager.workers == {}
    assert manager.registry == {}
    assert manager.health_probe is not None
    assert manager.launcher is not None
    assert manager.supervisor is not None


def test_process_manager_requires_runtime_registry():
    with pytest.raises(ValueError, match="requires WorkerRuntimeRegistry"):
        ProcessManager(None)


def test_register_service_def_and_health_path():
    manager = build_process_manager()

    manager.register_service_def("worker:stt", port=8765, script="backend_launcher.py", args=["--capability", "stt"])
    manager.set_health_path("worker:stt", "/ready")

    assert manager.registry["worker:stt"] == {
        "port": 8765,
        "script": "backend_launcher.py",
        "args": ["--capability", "stt"],
        "cwd": None,
        "health_path": "/ready",
    }


def test_start_worker_uses_launcher_and_records_worker_process():
    manager = build_process_manager()
    process = FakeProcess()
    manager.health_probe.is_service_reachable = MagicMock(return_value=(False, "none"))
    manager.launcher.build_launch_config = MagicMock(
        return_value={"cmd": ["python", "backend_launcher.py"], "env": {}, "display_name": "test"}
    )
    manager.launcher.launch = MagicMock(return_value=process)

    started = manager.start_worker("worker:test", script_name="backend_launcher.py", args=["--capability", "test"])

    assert started is True
    assert isinstance(manager.workers["worker:test"], WorkerProcess)
    assert manager.workers["worker:test"].process is process
    manager.launcher.launch.assert_called_once()


def test_start_worker_attaches_reachable_external_service():
    manager = build_process_manager()
    manager.register_service_def("worker:stt", port=8765)
    manager.health_probe.is_service_reachable = MagicMock(return_value=(True, "http"))

    started = manager.start_worker("worker:stt")

    assert started is True
    assert manager.workers["worker:stt"].is_external is True
    assert manager.workers["worker:stt"].process is None


def test_start_worker_respects_worker_runtime_readiness():
    registry = MagicMock()
    registry.runtime_for_capability.return_value = SimpleNamespace(id="stt-runtime")
    registry.resolve.return_value = SimpleNamespace(status="missing", entry_executable=None)
    manager = ProcessManager(registry)

    assert manager.start_worker("worker:stt", script_name="backend_launcher.py") is False


def test_is_running_detects_live_and_dead_processes():
    manager = build_process_manager()
    manager.workers["live"] = WorkerProcess(FakeProcess(returncode=None), time.time())
    manager.workers["dead"] = WorkerProcess(
        FakeProcess(returncode=1),
        time.time(),
        policy=RestartPolicy.NEVER,
    )

    assert manager.is_running("live") is True
    assert manager.is_running("dead") is False
    assert "dead" not in manager.workers


def test_stop_worker_terminates_managed_process_and_removes_record():
    manager = build_process_manager()
    process = FakeProcess()
    manager.workers["worker:test"] = WorkerProcess(process, time.time())

    manager.stop_worker("worker:test")

    assert process.terminated is True
    assert "worker:test" not in manager.workers


def test_get_active_workers_filters_dead_workers():
    manager = build_process_manager()
    manager.workers["live"] = WorkerProcess(FakeProcess(returncode=None), time.time())
    manager.workers["dead"] = WorkerProcess(
        FakeProcess(returncode=1),
        time.time(),
        policy=RestartPolicy.NEVER,
    )

    assert manager.get_active_workers() == ["live"]
    assert "dead" not in manager.workers


@pytest.mark.anyio
async def test_shutdown_all_stops_every_worker():
    manager = build_process_manager()
    process_a = FakeProcess(pid=1)
    process_b = FakeProcess(pid=2)
    manager.workers["a"] = WorkerProcess(process_a, time.time())
    manager.workers["b"] = WorkerProcess(process_b, time.time())

    await manager.shutdown_all()

    assert process_a.terminated is True
    assert process_b.terminated is True
    assert manager.workers == {}
