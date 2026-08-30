"""
Lumina Core Runtime Entry.
"""
import os
import sys

import uvicorn

def _extend_import_path() -> None:
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sys.path.append(current_dir)


_extend_import_path()

from app_config import config as app_settings
from core.api.app_factory import create_app
from services.container import create_service_container
from logger_setup import (
    request_id_ctx,
    setup_logger,
    uvicorn_access_log_enabled,
    uvicorn_log_level,
)

logger = setup_logger("lumina_core.log")
services = create_service_container()
app = create_app(logger, request_id_ctx, services)


if __name__ == "__main__":
    host = "127.0.0.1" if app_settings.network.bind_localhost_only else app_settings.network.host
    logger.info(f"🚀 Starting Server on {host}:{app_settings.network.core_port} (Localhost Only: {app_settings.network.bind_localhost_only})")
    uvicorn.run(
        app,
        host=host,
        port=app_settings.network.core_port,
        log_config=None,
        log_level=uvicorn_log_level(),
        access_log=uvicorn_access_log_enabled(),
    )
