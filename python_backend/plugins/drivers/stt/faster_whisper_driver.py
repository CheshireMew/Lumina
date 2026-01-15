import logging
import os
# from ..base import BaseSTTDriver
from core.interfaces.driver import BaseSTTDriver

logger = logging.getLogger("FasterWhisperDriver")

class FasterWhisperDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(
            id="faster-whisper",
            name="Faster Whisper",
            description="Standard robust model. Good accuracy, higher resource usage than SenseVoice."
        )
        self.model = None

    @property
    def supported_models(self) -> dict:
        return {
            "tiny": "75MB",
            "base": "150MB",
            "small": "500MB",
            "medium": "1.5GB",
            "large-v3": "3GB"
        }

    async def load(self):
        if self.model: return
        try:
            from faster_whisper import WhisperModel
            import app_config
            
            # Load config to get model size
            # For simplicity, default to 'base' or read from kwargs
            model_size = self.config.get("model_size", "base")
            device = "cuda" if os.environ.get("CUDA_VISIBLE_DEVICES") != "-1" else "cpu"
            # Auto-detect cuda availability more robustly? 
            # For now, assume CPU if not explicitly GPU configured.
            
            # We use a simplified load logic mimicking stt_server
            # app_config.MODELS_DIR / "faster-whisper" ...
            
            logger.info(f"Loading Faster Whisper ({model_size}) on {device}...")
            self.model = WhisperModel(model_size, device=device, compute_type="int8")
            logger.info("Faster Whisper Loaded")
            
        except Exception as e:
            logger.error(f"Failed to load Faster Whisper: {e}")
            raise e

    def transcribe(self, audio_data, **kwargs) -> str:
        if not self.model:
            raise RuntimeError("Faster Whisper not loaded")
            
        # Audio manager provides float32 numpy array usually
        segments, info = self.model.transcribe(audio_data, beam_size=5, language="zh") # Force ZH or auto
        
        text = " ".join([segment.text for segment in segments])
        return text.strip()
