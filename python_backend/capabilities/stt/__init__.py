
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from services.container import services
from .manager import STTPluginManager
from .routes import router as stt_router
from . import globals as stt_globals
from app_config import config as app_settings
from services.audio_manager import AudioManager
import numpy as np

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
        # 1. Initialize Manager
        manager = STTPluginManager()
        await manager.register_drivers()
        
        # 2. Register to Container
        services.register_stt(manager)
        
        # 3. Initialize Audio
        
        # Audio Callbacks (Moved from stt_server.py)
        def on_speech_start():
            logger.info("[AudioManager] Speech started")
            stt_globals.message_queue.put({"type": "vad_status", "status": "listening"})
        
        def on_speech_end(audio_data: np.ndarray):
            logger.info(f"[AudioManager] Speech ended. Length: {len(audio_data)}")
            stt_globals.message_queue.put({"type": "vad_status", "status": "thinking"})
            
            mgr = services.stt
            if not mgr:
                stt_globals.message_queue.put({"type": "vad_status", "status": "idle"})
                return
                
            try:
                 result = mgr.transcribe(audio_data)
                 full_text = result.get("text", "")
                 if full_text:
                     emotion = result.get("emotion")
                     language = result.get("language", "auto")
                     msg = {
                         "type": "transcription", 
                         "text": full_text, 
                         "language": language, 
                         "is_final": True
                     }
                     if emotion: msg["emotion"] = emotion
                     stt_globals.message_queue.put(msg)
                     logger.info(f"STT: {full_text} [{emotion or 'Neutral'}]")
    
            except Exception as e:
                logger.error(f"Transcribe Error: {e}")
                
            stt_globals.message_queue.put({"type": "vad_status", "status": "idle"})
    
        def on_vad_status_change(status: str):
            stt_globals.message_queue.put({"type": "vad_status", "status": status})
                
        # Initialize Global Audio Manager
        stt_globals.audio_manager = AudioManager(
            on_speech_start=on_speech_start,
            on_speech_end=on_speech_end,
            on_vad_status_change=on_vad_status_change,
            aggressiveness=1  # [Tuning] 1 = Lenient, 3 = Strict
        )
        logger.info("AudioManager initialized.")

    async def on_shutdown(self):
        if stt_globals.audio_manager:
            stt_globals.audio_manager.stop()
            
    def _gather_stt_state(self) -> List[Dict[str, Any]]:
        from services.container import services
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        stt_manager = getattr(services, 'stt', None)
        # Assuming port 8001 or config port. Generic Worker sets args, but config is reliable for default.
        stt_url = f"http://127.0.0.1:{config.network.stt_port}/models/switch"
        
        return DriverStateCollector.gather_driver_states(
            manager=stt_manager,
            category="stt",
            runtime_target="stt_server", # Keep identifier for now
            service_url=stt_url
        )
