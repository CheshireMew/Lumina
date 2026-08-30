import asyncio
import json
import os
import threading
from pathlib import Path
from types import SimpleNamespace

from config.models import CapabilitiesConfig
from routers.worker_proxy import get_worker_control_url
from services import parent_process
from services.worker_launcher import WorkerLauncher


PROJECT_ROOT = Path(__file__).parents[3]


def test_voice_workers_are_on_demand_by_default():
    payload = json.loads(
        (PROJECT_ROOT / "config" / "worker-runtimes.json").read_text("utf-8")
    )
    by_capability = {
        capability: item
        for item in payload["runtimes"]
        for capability in item.get("capabilities", [])
        if capability in {"stt", "tts"}
    }

    assert by_capability["stt"]["autoStart"] is False
    assert by_capability["tts"]["autoStart"] is False
    assert CapabilitiesConfig().prewarm_core is False


def test_retired_browser_vad_assets_are_outside_vite_public_dir():
    public_root = PROJECT_ROOT / "public"
    retired = [
        path
        for path in public_root.iterdir()
        if path.is_file() and path.suffix.lower() in {".wasm", ".onnx"}
    ]
    archive_root = (
        PROJECT_ROOT
        / "docs"
        / "archive"
        / "backend"
        / "unused-browser-vad"
        / "public-assets"
    )

    assert retired == []
    assert (archive_root / "silero_vad_v5.onnx").is_file()
    assert (archive_root / "ort-wasm-simd-threaded.wasm").is_file()


def test_worker_launches_are_owned_by_the_core_process():
    launcher = WorkerLauncher(
        SimpleNamespace(runtime_for_capability=lambda _capability: None),
        base_dir=PROJECT_ROOT / "python_backend",
    )
    environment = {}

    launcher._apply_runtime_environment("worker:stt", environment)

    assert environment["LUMINA_PARENT_PID"] == str(os.getpid())


def test_parent_watchdog_requests_shutdown_when_owner_exits(monkeypatch):
    shutdown_requested = threading.Event()
    states = iter([True, False])
    monkeypatch.setenv("LUMINA_PARENT_PID", "424242")
    monkeypatch.setattr(
        parent_process,
        "_process_is_running",
        lambda _process_id: next(states),
    )

    thread = parent_process.start_parent_watchdog(
        shutdown_requested.set,
        interval_seconds=0.001,
    )

    assert thread is not None
    assert shutdown_requested.wait(timeout=1)


def test_registered_worker_proxy_uses_discovery_without_extra_health_probe():
    process_manager = SimpleNamespace(is_running=lambda _target: True)
    worker_node = SimpleNamespace(base_url="http://127.0.0.1:8765")
    container = SimpleNamespace(
        get_worker_runtime_registry=lambda: SimpleNamespace(
            runtime_for_capability=lambda _capability: None
        ),
        get_process_manager=lambda: process_manager,
        get_worker_discovery=lambda: SimpleNamespace(
            get_node=lambda _worker_id: worker_node
        ),
    )

    upstream = asyncio.run(get_worker_control_url("stt", container))

    assert upstream == worker_node.base_url
