import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import MagicMock

import pytest


PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


def test_worker_runtime_container_services_are_reset_for_worker_process():
    from services.worker_runtime.host import app_settings
    from services.worker_runtime import WorkerRuntimeHost, WorkerRuntimeOptions

    container = MagicMock()
    container.has_service.return_value = True
    host = WorkerRuntimeHost(
        WorkerRuntimeOptions(capability="stt", port=8765, runtime_target="worker:stt"),
        container,
    )

    host._initialize_container_services()

    container.set_config.assert_called_once_with(app_settings)
    container.set_event_bus.assert_called_once()
    container.set_capability_registry.assert_called_once()
    container.set_worker_runtime_registry.assert_called_once()
    container.has_service.assert_not_called()


@pytest.mark.anyio
async def test_worker_runtime_shutdown_stops_config_watcher():
    from services.worker_runtime import WorkerRuntimeHost, WorkerRuntimeOptions

    stop_order = []

    class ConfigWatcher:
        def stop(self):
            stop_order.append("config_watcher")

    async def sleeper():
        try:
            while True:
                await __import__("asyncio").sleep(10)
        finally:
            stop_order.append("config_task")

    app = SimpleNamespace(state=SimpleNamespace())
    app.state.config_watcher = ConfigWatcher()
    config_watcher_task = __import__("asyncio").create_task(sleeper())
    app.state.config_watcher_task = config_watcher_task

    host = WorkerRuntimeHost(
        WorkerRuntimeOptions(capability="stt", port=8765, runtime_target="worker:stt"),
        MagicMock(),
    )

    await host.shutdown(app)

    assert stop_order == ["config_watcher"]
    assert config_watcher_task.cancelled()
