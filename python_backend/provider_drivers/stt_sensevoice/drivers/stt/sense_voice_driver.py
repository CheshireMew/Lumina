import sys
import os
import logging
from core.interfaces.driver import BaseSTTDriver

logger = logging.getLogger("SenseVoiceDriver")

class SenseVoiceDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(
            id="driver.stt.sensevoice",
            name="SenseVoice (Sherpa-ONNX)",
            description="Ultra-fast, high-accuracy model from Alibaba. Optimized for CPU."
        )
        self.engine = None

    def load(self):
        """
        Synchronous load (CPU heavy). 
        STTProviderManager wraps this in run_in_executor.
        """
        if self.engine: return
        try:
            # Ensure we can import from root if needed
            # 1. Add 'python_backend' folder to sys.path for dynamic loading.
            backend_path = os.path.join(os.getcwd(), "python_backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)
            
            # Ensure Root Directory is in sys.path to allow 'from python_backend...' imports
            root_dir = os.path.dirname(backend_path)
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)

            from .sensevoice.engine import SenseVoiceEngine
            
            # We assume model path is managed by app_config or passed here.
            # For now, let the engine handle its internal paths as before.
            logger.info("DEBUG: Instantiating SenseVoiceEngine...")
            self.engine = SenseVoiceEngine()
            
            logger.info("SenseVoice Driver Loaded")
        except Exception as e:
            logger.error(f"Failed to load SenseVoice: {e}", exc_info=True)
            raise e

    def transcribe(self, audio_data, **kwargs) -> dict:
        if not self.engine:
            raise RuntimeError("Driver not loaded")
            
        segments, info = self.engine.transcribe(audio_data)
        full_text = "".join([s.text.strip() for s in segments])
        
        return {
            "text": full_text,
            "language": info.language,
            "emotion": getattr(info, 'emotion', None),
            "provider": getattr(info, 'provider', None),
            "confidence": 1.0 # SenseVoice doesn't give confidence yet?
        }
