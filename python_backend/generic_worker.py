"""
Generic worker entrypoint.

This file stays intentionally thin: argument parsing, environment setup,
runtime host creation, and uvicorn launch.
"""

import argparse
import os
import sys

import uvicorn

from logger_setup import uvicorn_access_log_enabled, uvicorn_log_level
from services.container import create_service_container
from services.parent_process import start_parent_watchdog
from services.worker_runtime import WorkerRuntimeHost, WorkerRuntimeOptions

if os.name == "nt":
    try:
        os.add_dll_directory(os.path.dirname(os.path.abspath(__file__)))
    except Exception:
        pass


def parse_args() -> WorkerRuntimeOptions:
    parser = argparse.ArgumentParser(description="Lumina Generic Worker")
    parser.add_argument("--capability", type=str, required=True, help="Capability to load (stt, tts, ocr...)")
    parser.add_argument("--port", type=int, help="Override port")
    parser.add_argument("--host", type=str, default="127.0.0.1")
    parser.add_argument("--runtime-target", type=str, help="Override runtime target")
    args, _ = parser.parse_known_args()
    return WorkerRuntimeOptions(
        capability=args.capability,
        host=args.host,
        port=args.port,
        runtime_target=args.runtime_target,
    )


if __name__ == "__main__":
    runtime_options = parse_args()
    runtime_host = WorkerRuntimeHost(runtime_options, create_service_container())
    app = runtime_host.build_app()

    runtime_host.logger.info(
        "Starting generic worker [%s] on port %s",
        runtime_options.capability,
        runtime_host.listen_port,
    )
    runtime_config = uvicorn.Config(
        app,
        host=runtime_options.host,
        port=runtime_host.listen_port,
        log_level=uvicorn_log_level(),
        access_log=uvicorn_access_log_enabled(),
    )
    server = uvicorn.Server(runtime_config)
    app.state.request_runtime_shutdown = lambda: setattr(server, "should_exit", True)
    start_parent_watchdog(app.state.request_runtime_shutdown, logger=runtime_host.logger)
    server.run()
