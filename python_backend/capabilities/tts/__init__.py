
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from core.runtime import resolve_contract_url, runtime_target_for_capability
from services.managers.tts import TTSProviderManager
from .routes import router as tts_router
from .runtime_state import get_tts_runtime_state
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
        state = get_tts_runtime_state()
        state.reset()
        container = app.state.services
        manager = TTSProviderManager(config=app_settings)
        await manager.register_drivers()
        
        container.set_tts(manager)
        state.tts_manager = manager
        logger.info(f"TTS Service Ready. Active Driver: {manager.active_driver_id}")

    async def on_shutdown(self):
        get_tts_runtime_state().reset()

    def _gather_tts_state(self) -> List[Dict[str, Any]]:
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        tts_manager = get_tts_runtime_state().tts_manager
        tts_url = resolve_contract_url(config, "tts", "switch")
        
        return DriverStateCollector.gather_driver_states(
            manager=tts_manager,
            category="tts",
            runtime_target=runtime_target_for_capability("tts"),
            service_url=tts_url
        )
