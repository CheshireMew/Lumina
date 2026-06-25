import asyncio
import logging
import re
import uuid

import numpy as np

from services.audio_filter_chain import AudioFilterChain
from services.managers.audio import AudioManager

from .runtime_state import SttRuntimeState

logger = logging.getLogger("STTAudioRuntime")

FILLER_TRANSCRIPTIONS = {
    "\u55ef",
    "\u6069",
    "\u5453",
    "\u989d",
    "\u554a",
    "\u54e6",
    "\u55ef\u55ef",
}
MAX_FILLER_AUDIO_SECONDS = 1.8
MAX_FILLER_AUDIO_RMS = 0.03


class SttAudioRuntime:
    def __init__(self, state: SttRuntimeState, manager):
        self._state = state
        self._manager = manager

    def start(self) -> AudioManager:
        self._state.filter_chain = AudioFilterChain.instance()
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            loop = asyncio.get_event_loop()

        def on_speech_start():
            logger.info("[AudioManager] Speech started")
            self._state.message_queue.put({"type": "vad_status", "status": "listening"})

        def on_speech_end(audio_data: np.ndarray):
            audio_id = str(uuid.uuid4())[:8]
            logger.debug("[AudioManager] Speech ended. ID: %s, Length: %s", audio_id, len(audio_data))
            self._state.message_queue.put({"type": "vad_status", "status": "thinking"})

            future = asyncio.run_coroutine_threadsafe(
                self._process_audio_pipeline(audio_id, audio_data),
                loop,
            )
            future.add_done_callback(
                lambda item: logger.error("Audio pipeline error: %s", item.exception())
                if item.exception()
                else None
            )

        def on_vad_status_change(status: str):
            self._state.message_queue.put({"type": "vad_status", "status": status})

        self._state.audio_manager = AudioManager(
            on_speech_start=on_speech_start,
            on_speech_end=on_speech_end,
            on_vad_status_change=on_vad_status_change,
        )
        logger.info("AudioManager initialized.")
        return self._state.audio_manager

    async def _process_audio_pipeline(self, audio_id: str, audio_data: np.ndarray):
        chain = AudioFilterChain.instance()
        should_continue, reason = await chain.process(
            audio_data,
            sample_rate=16000,
            metadata={"audio_id": audio_id},
        )

        if not should_continue:
            logger.info("Audio %s rejected: %s", audio_id, reason)
            self._state.message_queue.put({"type": "vad_status", "status": "idle"})
            return

        manager = self._manager
        if not manager:
            self._state.message_queue.put({"type": "vad_status", "status": "idle"})
            return

        try:
            current_loop = asyncio.get_running_loop()
            result = await current_loop.run_in_executor(None, manager.transcribe, audio_data)

            full_text = result.get("text", "")
            if self._should_drop_transcription(full_text, audio_data):
                logger.info("Dropped likely STT filler hallucination: %s", full_text)
                full_text = ""

            if full_text:
                emotion = result.get("emotion")
                language = result.get("language", "auto")
                message = {
                    "type": "transcription",
                    "text": full_text,
                    "language": language,
                    "audio_id": audio_id,
                    "is_final": True,
                }
                if emotion:
                    message["emotion"] = emotion
                self._state.message_queue.put(message)
                logger.info("STT: %s [%s]", full_text, emotion or "Neutral")
        except Exception as exc:
            logger.error("Transcribe Error: %s", exc)

        self._state.message_queue.put({"type": "vad_status", "status": "idle"})

    def _should_drop_transcription(self, text: str, audio_data: np.ndarray) -> bool:
        normalized = self._normalize_transcription(text)
        if normalized not in FILLER_TRANSCRIPTIONS:
            return False

        duration_seconds = len(audio_data) / 16000
        rms = float(np.sqrt(np.mean(audio_data**2))) if len(audio_data) else 0.0
        return (
            duration_seconds <= MAX_FILLER_AUDIO_SECONDS
            and rms <= MAX_FILLER_AUDIO_RMS
        )

    def _normalize_transcription(self, text: str) -> str:
        without_tags = re.sub(r"<\|?[A-Z]+\|?>", "", text)
        return re.sub(r"[\s,，.。!！?？~～…]+", "", without_tags)
