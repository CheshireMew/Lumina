
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from core.runtime import resolve_contract_url, runtime_target_for_capability
from services.audio_filter_chain import AudioFilterChain
from services.managers.stt import STTProviderManager
from .routes import router as stt_router
from . import globals as stt_globals
from app_config import config as app_settings
from services.managers.audio import AudioManager
import numpy as np
import asyncio
import uuid

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
        container = app.state.container
        # 1. Initialize Manager
        manager = STTProviderManager(config=app_settings)
        await manager.register_drivers()
        
        # 2. Register to Container
        container.set_stt(manager)
        stt_globals.stt_manager = manager
        
        # 3. Initialize audio filter chain
        filter_chain = AudioFilterChain.instance()
        stt_globals.filter_chain = filter_chain
        
        # 4. Initialize Audio
        
        # Create async loop reference for thread-safe callbacks
        # Note: on_startup runs in the event loop, so get_running_loop() works
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()
        
        def on_speech_start():
            logger.info("[AudioManager] Speech started")
            stt_globals.message_queue.put({"type": "vad_status", "status": "listening"})
        
        def on_speech_end(audio_data: np.ndarray):
            """
            Audio callback - runs in sounddevice thread.
            MUST NOT BLOCK.
            Schedules async processing via run_coroutine_threadsafe.
            """
            audio_id = str(uuid.uuid4())[:8]
            logger.debug(f"[AudioManager] Speech ended. ID: {audio_id}, Length: {len(audio_data)}")
            
            # Post 'thinking' status immediately
            stt_globals.message_queue.put({"type": "vad_status", "status": "thinking"})
            
            # Schedule async processing in the main event loop
            fut = asyncio.run_coroutine_threadsafe(
                _process_audio_pipeline(audio_id, audio_data),
                loop
            )
            fut.add_done_callback(lambda f: logger.error(f"Audio pipeline error: {f.exception()}") if f.exception() else None)

        async def _process_audio_pipeline(audio_id: str, audio_data: np.ndarray):
            """
            Async pipeline: Filter Chain -> STT Transcription
            """
            # 1. Run through Filter Chain
            chain = AudioFilterChain.instance()
            should_continue, reason = await chain.process(
                audio_data,
                sample_rate=16000,
                metadata={"audio_id": audio_id}
            )
            
            if not should_continue:
                logger.info(f"🔇 Audio {audio_id} rejected: {reason}")
                stt_globals.message_queue.put({"type": "vad_status", "status": "idle"})
                return

            # 2. STT Transcription
            mgr = manager
            if not mgr:
                stt_globals.message_queue.put({"type": "vad_status", "status": "idle"})
                return
                
            try:
                # Offload CPU-bound transcription to executor
                current_loop = asyncio.get_running_loop()
                result = await current_loop.run_in_executor(None, mgr.transcribe, audio_data)
                
                full_text = result.get("text", "")
                if full_text:
                    emotion = result.get("emotion")
                    language = result.get("language", "auto")
                    msg = {
                        "type": "transcription", 
                        "text": full_text, 
                        "language": language,
                        "audio_id": audio_id,
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
        from services.reporting.driver_state_collector import DriverStateCollector
        from app_config import config
        
        stt_manager = stt_globals.stt_manager
        stt_url = resolve_contract_url(config, "stt", "switch")
        
        return DriverStateCollector.gather_driver_states(
            manager=stt_manager,
            category="stt",
            runtime_target=runtime_target_for_capability("stt"),
            service_url=stt_url
        )
