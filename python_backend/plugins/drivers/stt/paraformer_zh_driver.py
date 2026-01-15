import logging
import sys
import os
from plugins.drivers.base import BaseSTTDriver

logger = logging.getLogger("ParaformerZHDriver")

class ParaformerZHDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(
            id="paraformer-zh",
            name="Paraformer (Chinese)",
            description="Highly accurate Chinese ASR (Sherpa-ONNX). Good for meetings."
        )
        self.enabled = True # Default enabled
        self.engine = None
        self._loaded = False

    async def load(self):
        if self._loaded and self.engine:
            return

        try:
            logger.info("Initializing Paraformer (ZH) Engine...")
            if "python_backend" not in sys.modules:
                sys.path.append(os.path.join(os.getcwd(), "python_backend"))
            
            from .paraformer.engine import ParaformerEngine
            self.engine = ParaformerEngine(language="zh")
            # Using sync initialization for now as ParaformerEngine is sync
            self.engine.initialize()
            self._loaded = True
            logger.info("Paraformer (ZH) Engine loaded successfully.")
        except Exception as e:
            logger.error(f"Failed to load Paraformer (ZH): {e}", exc_info=True)
            self._loaded = False
            raise e

    def transcribe(self, audio_data, **kwargs):
        if not self._loaded or not self.engine:
            raise RuntimeError("Driver not loaded")
        
        # Paraformer engine returns (segments, info)
        return self.engine.transcribe(audio_data, **kwargs)
