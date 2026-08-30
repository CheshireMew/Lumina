import argparse
import multiprocessing
import os
import sys

_BACKEND_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.append(_BACKEND_DIR)

from app_config import config
from core.runtime import resolve_runtime_port, runtime_target_for_capability
from logger_setup import uvicorn_access_log_enabled, uvicorn_log_level
from services.parent_process import start_parent_watchdog


def run_core():
    import main as core_app
    import uvicorn

    host = "127.0.0.1" if config.network.bind_localhost_only else config.network.host
    port = config.network.core_port
    print(f"[Launcher] Starting Core System on {host}:{port}...", flush=True)
    runtime_config = uvicorn.Config(
        core_app.app,
        host=host,
        port=port,
        log_level=uvicorn_log_level(),
        log_config=None,
        access_log=uvicorn_access_log_enabled(),
    )
    server = uvicorn.Server(runtime_config)
    core_app.app.state.request_runtime_shutdown = lambda: setattr(server, "should_exit", True)
    start_parent_watchdog(core_app.app.state.request_runtime_shutdown)
    server.run()


def run_worker(capability: str):
    import uvicorn
    from services.container import create_service_container
    from services.worker_runtime import WorkerRuntimeHost, WorkerRuntimeOptions

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
    runtime_host = WorkerRuntimeHost(runtime_options, create_service_container())
    app = runtime_host.build_app()

    print(f"[Launcher] Starting Worker Host [{capability}] on {config.network.host}:{port}...", flush=True)
    runtime_config = uvicorn.Config(
        app,
        host=config.network.host,
        port=runtime_host.listen_port,
        log_level=uvicorn_log_level(),
        log_config=None,
        access_log=uvicorn_access_log_enabled(),
    )
    server = uvicorn.Server(runtime_config)
    app.state.request_runtime_shutdown = lambda: setattr(server, "should_exit", True)
    start_parent_watchdog(app.state.request_runtime_shutdown, logger=runtime_host.logger)
    server.run()


def _resolve_launcher_mode(name: str) -> tuple[str, str | None]:
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
        mode, inferred_capability = _resolve_launcher_mode(cli_args.mode)
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
            log_path = os.path.join(str(config.data_root), "logs", "backend_crash.log")
            with open(log_path, "a", encoding="utf-8") as handle:
                handle.write(f"\n--- Crash Report [{cli_args.mode}] ---\n")
                handle.write(traceback.format_exc())
        except Exception:
            pass
        sys.exit(1)
