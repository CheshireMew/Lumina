from core.interfaces.driver import BaseTTSDriver
import logging

logger = logging.getLogger("MockTTS")

class MockTTSDriver(BaseTTSDriver):
    def __init__(self):
        super().__init__(id="mock-tts", name="Mock TTS (Extension)")

    async def load(self):
        logger.info("Mock TTS Loaded from Extension!")
        
    async def generate_stream(self, text: str, voice: str, **kwargs):
        yield b'\x00' * 1024
