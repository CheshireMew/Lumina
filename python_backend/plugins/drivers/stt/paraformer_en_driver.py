import logging
import sys
import os
from plugins.drivers.base import BaseSTTDriver

logger = logging.getLogger("ParaformerENDriver")

class ParaformerENDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(
            id="paraformer-en",
            name="Paraformer (English)",
            description="Highly accurate English ASR (Sherpa-ONNX)."
        )
        self.enabled = True
        self.engine = None
        self._loaded = False

    async def load(self):
        if self._loaded and self.engine:
            return

        try:
            logger.info("Initializing Paraformer (EN) Engine...")
            if "python_backend" not in sys.modules:
                sys.path.append(os.path.join(os.getcwd(), "python_backend"))
            
            from .paraformer.engine import ParaformerEngine
            # Assuming ParaformerEngine supports language="en" config
            self.engine = ParaformerEngine(language="en")
            self.engine.initialize()
            self._loaded = True
            logger.info("Paraformer (EN) Engine loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Paraformer (EN): {e}", exc_info=True)
            self._loaded = False
            raise e

    def transcribe(self, audio_data, **kwargs):
        if not self._loaded or not self.engine:
            raise RuntimeError("Driver not loaded")
        
        return self.engine.transcribe(audio_data, **kwargs)
