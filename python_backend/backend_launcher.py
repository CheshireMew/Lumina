import argparse
import multiprocessing
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_BACKEND_DIR)
sys.path.append(os.path.join(_BACKEND_DIR, "sdk"))

from app_config import config
from core.runtime import resolve_runtime_port, runtime_target_for_capability


def run_core():
    import main as core_app
    import uvicorn

    host = "127.0.0.1" if config.network.bind_localhost_only else config.network.host
    port = config.network.memory_port
    print(f"[Launcher] Starting Core System on {host}:{port}...", flush=True)
    uvicorn.run(core_app.app, host=host, port=port, log_level="info", log_config=None)


def run_worker(capability: str):
    import uvicorn
    from core.capability_packages import CapabilityPackageRegistry
    from services.container import services
    from services.worker_runtime import WorkerRuntimeHost, WorkerRuntimeOptions

    services.set_capability_package_registry(CapabilityPackageRegistry())
    runtime_target = runtime_target_for_capability(capability)
    port = resolve_runtime_port(config, runtime_target)
    if not port:
        raise ValueError(f"No port configured for capability '{capability}'")

    runtime_options = WorkerRuntimeOptions(
        capability=capability,
        host=config.network.host,
        port=port,
        runtime_target=runtime_target,
    )
    runtime_host = WorkerRuntimeHost(runtime_options, services)
    app = runtime_host.build_app()

    print(f"[Launcher] Starting Worker Host [{capability}] on {config.network.host}:{port}...", flush=True)
    uvicorn.run(app, host=config.network.host, port=runtime_host.listen_port, log_level="info", log_config=None)


def _resolve_legacy_service(name: str) -> tuple[str, str | None]:
    if name == "core":
        return ("core", None)
    if name == "worker":
        return ("worker", None)
    raise ValueError(f"Unknown launcher mode: {name}")


if __name__ == "__main__":
    multiprocessing.freeze_support()

    parser = argparse.ArgumentParser(description="Lumina Runtime Launcher")
    parser.add_argument("mode", help="core | worker")
    parser.add_argument("--capability", help="Capability hosted by worker mode")
    cli_args = parser.parse_args()

    try:
        mode, inferred_capability = _resolve_legacy_service(cli_args.mode)
        if mode == "core":
            run_core()
        else:
            capability = cli_args.capability or inferred_capability
            if not capability:
                raise ValueError("Worker mode requires --capability")
            run_worker(capability)
    except KeyboardInterrupt:
        print("[Launcher] Service stopped by user.", flush=True)
    except Exception as exc:
        print(f"[Launcher] Critical Error: {exc}", flush=True)
        import traceback

        traceback.print_exc()
        try:
            log_path = os.path.join(os.path.expanduser("~"), "lumina_backend_crash.log")
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"\n--- Crash Report [{cli_args.mode}] ---\n")
                handle.write(traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)
