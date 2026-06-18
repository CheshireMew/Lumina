import importlib
import logging
from typing import Any

from core.runtime import resolve_runtime_port, runtime_target_for_capability

from .types import WorkerRuntimeOptions


def resolve_worker_port(app_settings: Any, options: WorkerRuntimeOptions) -> int:
    if options.port:
        return options.port

    runtime_target = options.runtime_target or runtime_target_for_capability(options.capability)
    resolved = resolve_runtime_port(app_settings, runtime_target)
    return resolved or 8000


def load_capability(capability_name: str, logger: logging.Logger):
    module_path = f"capabilities.{capability_name}"
    logger.info("Loading worker capability: %s", module_path)

    module = importlib.import_module(module_path)
    if hasattr(module, "Capability"):
        return module.Capability()
    if hasattr(module, "get_capability"):
        return module.get_capability()

    raise ImportError(
        f"Module {module_path} does not export 'Capability' class or 'get_capability' function"
    )
