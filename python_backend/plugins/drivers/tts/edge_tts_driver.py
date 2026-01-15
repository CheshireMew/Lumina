import logging
from typing import AsyncGenerator
import edge_tts
from core.interfaces.driver import BaseTTSDriver

logger = logging.getLogger("EdgeTTSDriver")

class EdgeTTSDriver(BaseTTSDriver):
    def __init__(self):
        super().__init__(
            id="edge-tts",
            name="Edge TTS (Online)",
            description="Microsoft Edge Online TTS. Free, fast, high quality but requires internet."
        )

    async def load(self):
        # Edge TTS is stateless, nothing to load
        logger.info("EdgeTTS Driver loaded (Stateless)")

    async def generate_stream(self, text: str, voice: str = "zh-CN-XiaoxiaoNeural", **kwargs) -> AsyncGenerator[bytes, None]:
        """
        Generates audio using edge-tts communicate.
        """
        rate = kwargs.get("rate", "+0%")
        pitch = kwargs.get("pitch", "+0Hz")
        
        communicate = edge_tts.Communicate(text, voice, rate=rate, pitch=pitch)
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                yield chunk["data"]
