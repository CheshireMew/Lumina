import logging
from typing import AsyncGenerator
from core.interfaces.driver import BaseTTSDriver

logger = logging.getLogger("EdgeTTSDriver")

class EdgeTTSDriver(BaseTTSDriver):
    def __init__(self):
        super().__init__(
            id="driver.tts.edge",
            name="Edge TTS (Online)",
            description="Microsoft Edge Online TTS. Free, fast, high quality but requires internet."
        )

    async def load(self):
        import edge_tts  # noqa: F401

        # Edge TTS is stateless, but the runtime dependency must be present.
        logger.info("EdgeTTS Driver loaded (Stateless)")

    async def list_voices(self):
        try:
            import edge_tts

            voices = await edge_tts.list_voices()
        except Exception as exc:
            logger.error(f"EdgeTTS voice list error: {exc}")
            return []

        normalized = []
        for voice in voices:
            normalized.append(
                {
                    "name": voice.get("ShortName") or voice.get("Name") or "",
                    "gender": voice.get("Gender") or "Unknown",
                    "locale": voice.get("Locale") or voice.get("LocaleName") or "",
                }
            )
        return normalized

    @property
    def config_schema(self):
        return {
            "key": "voice_config",
            "fields": [
                {"key": "voiceId", "label": "Voice", "type": "select", "optionSource": "edgeVoices"},
                {"key": "rate", "label": "Rate", "type": "text", "default": "+0%"},
                {"key": "pitch", "label": "Pitch", "type": "text", "default": "+0Hz"}
            ]
        }

    async def generate_stream(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural", **kwargs) -> AsyncGenerator[bytes, None]:
        """
        Generates audio using edge-tts communicate.
        """
        if not text or not text.strip():
            logger.warning("EdgeTTS received empty text. Skipping.")
            return

        rate = kwargs.get("rate", "+0%")
        pitch = kwargs.get("pitch", "+0Hz")
        
        # Ensure rate/pitch format
        if not isinstance(rate, str): rate = "+0%"
        if not isinstance(pitch, str): pitch = "+0Hz"

        try:
            import edge_tts

            communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
            
            async for chunk in communicate.stream():
                if chunk["type"] == "audio":
                    yield chunk["data"]
        except Exception as e:
            logger.error(f"EdgeTTS Stream Error: {e}")
            raise e
