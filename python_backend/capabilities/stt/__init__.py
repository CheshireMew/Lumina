
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from core.runtime import resolve_contract_url, runtime_target_for_capability
from services.managers.stt import STTProviderManager
from .routes import router as stt_router
from .audio_runtime import SttAudioRuntime
from .runtime_state import get_stt_runtime_state
from app_config import config as app_settings

logger = logging.getLogger("STTCapability")

class Capability(IWorkerCapability):
    @property
    def name(self) -> str:
        return "stt"

    def register_routes(self, app: FastAPI):
        app.include_router(stt_router)

    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        return self._gather_stt_state

    async def on_startup(self, app: FastAPI):
        state = get_stt_runtime_state()
        state.reset()
        container = app.state.services
        # 1. Initialize Manager
        manager = STTProviderManager(config=app_settings)
        await manager.register_drivers()
        
        # 2. Register to Container
        container.set_stt(manager)
        state.stt_manager = manager

        if app_settings.is_provider_desired_enabled("system.voiceprint"):
            from services.voiceprint_filter import VoiceprintFilter

            voiceprint_filter = VoiceprintFilter(app_settings)
            await voiceprint_filter.start()
            container.set_voiceprint_filter(voiceprint_filter)
            state.voiceprint_manager = voiceprint_filter

        SttAudioRuntime(state, manager).start()

    async def on_shutdown(self):
        state = get_stt_runtime_state()
        voiceprint_filter = state.voiceprint_manager
        if voiceprint_filter and hasattr(voiceprint_filter, "stop"):
            await voiceprint_filter.stop()
        if state.audio_manager:
            state.audio_manager.stop()
        state.reset()
            
    def _gather_stt_state(self) -> List[Dict[str, Any]]:
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        state = get_stt_runtime_state()
        stt_manager = state.stt_manager
        stt_url = resolve_contract_url(config, "stt", "switch")
        
        return DriverStateCollector.gather_driver_states(
            manager=stt_manager,
            category="stt",
            runtime_target=runtime_target_for_capability("stt"),
            service_url=stt_url
        )
