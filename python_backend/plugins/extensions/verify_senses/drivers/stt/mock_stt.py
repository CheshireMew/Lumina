from core.interfaces.driver import BaseSTTDriver
import logging

logger = logging.getLogger("MockSTT")

class MockSTTDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(id="mock-stt", name="Mock STT (Extension)")
        
    def load(self):
        logger.info("Mock STT Loaded from Extension!")
        
    def transcribe(self, audio_data, **kwargs):
        return "This is a mock transcription from an extension."
