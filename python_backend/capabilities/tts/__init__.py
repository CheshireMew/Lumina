
import logging
import httpx
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from core.runtime import resolve_contract_url, runtime_target_for_capability
from services.managers.tts import TTSProviderManager
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
        container = app.state.container
        # 1. Initialize HTTP Client
        tts_globals.http_client = httpx.AsyncClient(timeout=httpx.Timeout(60.0, connect=10.0))
        
        # 2. Initialize Manager
        manager = TTSProviderManager(config=app_settings)
        await manager.register_drivers()
        
        # 3. Register to Container
        container.set_tts(manager)
        tts_globals.tts_manager = manager
        logger.info(f"TTS Service Ready. Active Driver: {manager.active_driver_id}")

    async def on_shutdown(self):
        if tts_globals.http_client:
            await tts_globals.http_client.aclose()

    def _gather_tts_state(self) -> List[Dict[str, Any]]:
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        tts_manager = tts_globals.tts_manager
        tts_url = resolve_contract_url(config, "tts", "switch")
        
        return DriverStateCollector.gather_driver_states(
            manager=tts_manager,
            category="tts",
            runtime_target=runtime_target_for_capability("tts"),
            service_url=tts_url
        )
