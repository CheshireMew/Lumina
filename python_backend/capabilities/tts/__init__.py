
import logging
import httpx
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from services.container import services
from .manager import TTSPluginManager
from .routes import router as tts_router
from . import globals as tts_globals
from app_config import config as app_settings

logger = logging.getLogger("TTSCapability")

class Capability(IWorkerCapability):
    @property
    def name(self) -> str:
        return "tts"

    def register_routes(self, app: FastAPI):
        app.include_router(tts_router)

    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        return self._gather_tts_state

    async def on_startup(self, app: FastAPI):
        # 1. Initialize HTTP Client
        tts_globals.http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        
        # 2. Initialize Manager
        manager = TTSPluginManager()
        await manager.register_drivers()
        
        # 3. Register to Container
        services.register_tts(manager)
        logger.info(f"TTS Service Ready. Active Driver: {manager.active_driver_id}")

    async def on_shutdown(self):
        if tts_globals.http_client:
            await tts_globals.http_client.aclose()

    def _gather_tts_state(self) -> List[Dict[str, Any]]:
        from services.container import services
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        tts_manager = getattr(services, 'tts', None)
        # Port lookup
        tts_url = f"http://127.0.0.1:{config.network.tts_port}/models/switch"
        
        return DriverStateCollector.gather_driver_states(
            manager=tts_manager,
            category="tts",
            runtime_target="tts_server",
            service_url=tts_url
        )
