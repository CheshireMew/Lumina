import logging
import asyncio
from typing import Dict, Any, Optional

from python_backend.core.plugins.interface import TTSPlugin

logger = logging.getLogger("EdgeTTSPlugin")

# Lazy import
try:
    import edge_tts
except ImportError:
    edge_tts = None

class Plugin(TTSPlugin):
    def __init__(self):
        self._name = "tts:edge_tts"
        self._version = "1.0.0"
        self.default_voice = "zh-CN-XiaoxiaoNeural"
        self.rate = "+0%"
        self.pitch = "+0Hz"

    @property
    def name(self) -> str:
        return self._name

    @property
    def version(self) -> str:
        return self._version

    def load(self, config: Dict[str, Any]) -> bool:
        if edge_tts is None:
            logger.error("edge_tts not installed.")
            return False
        
        self.default_voice = config.get("voice", self.default_voice)
        self.rate = config.get("rate", self.rate)
        self.pitch = config.get("pitch", self.pitch)
        
        logger.info(f"EdgeTTS plugin loaded. Default voice: {self.default_voice}")
        return True

    async def generate(self, text: str, output_path: str, voice_id: Optional[str] = None) -> str:
        if edge_tts is None:
            raise RuntimeError("EdgeTTS plugin not loaded")

        voice = voice_id if voice_id else self.default_voice
        
        # EdgeTTS Communicate object
        communicate = edge_tts.Communicate(text, voice, rate=self.rate, pitch=self.pitch)
        
        # Save directly to file
        await communicate.save(output_path)
        
        return output_path
