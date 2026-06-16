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
from logger_setup import request_id_ctx, setup_logger

logger = setup_logger("lumina_core.log")
app = create_app(logger, request_id_ctx)


if __name__ == "__main__":
    host = "127.0.0.1" if app_settings.network.bind_localhost_only else app_settings.network.host
    logger.info(f"🚀 Starting Server on {host}:{app_settings.network.memory_port} (Localhost Only: {app_settings.network.bind_localhost_only})")
    uvicorn.run(app, host=host, port=app_settings.network.memory_port, log_config=None)
