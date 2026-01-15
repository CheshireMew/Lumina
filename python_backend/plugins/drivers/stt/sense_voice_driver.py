import sys
import os
import logging
# Ensure we can import from root if needed
# from ..base import BaseSTTDriver # Relative fails in dynamic load
from core.interfaces.driver import BaseSTTDriver

logger = logging.getLogger("SenseVoiceDriver")

class SenseVoiceDriver(BaseSTTDriver):
    def __init__(self):
        super().__init__(
            id="sense-voice",
            name="SenseVoice (Sherpa-ONNX)",
            description="Ultra-fast, high-accuracy model from Alibaba. Optimized for CPU."
        )
        self.engine = None

    async def load(self):
        if self.engine: return
        try:
            # Ensure we can import 'plugins' as a top-level package
            # 1. Add 'python_backend' folder (which contains 'plugins') to sys.path
            backend_path = os.path.join(os.getcwd(), "python_backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)
            
            # 2. Add 'python_backend/plugins' to sys.path just in case? No, better use standard package structure.
            # If structure is python_backend/plugins/drivers/stt/sensevoice
            # Then 'from plugins.drivers...' works if python_backend conforms to package
            
            # Ensure Root Directory is in sys.path to allow 'from python_backend...' imports
            # This handles cases where PYTHONPATH is set to python_backend/ only.
            root_dir = os.path.dirname(backend_path)
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)

            # 3. Import Engine
            try:
                # Try absolute import from root (preferred)
                from python_backend.plugins.drivers.stt.sensevoice.engine import SenseVoiceEngine
            except ImportError:
                try:
                     # Fallback to local import if we are somehow inside the package structure differently
                     from plugins.drivers.stt.sensevoice.engine import SenseVoiceEngine
                except ImportError as ie:
                    logger.error(f"Failed to import SenseVoiceEngine: {ie}. Path: {sys.path}")
                    raise ie
            
            # We assume model path is managed by app_config or passed here.
            # For now, let the engine handle its internal paths as before.
            self.engine = SenseVoiceEngine()
            # self.engine.load_model(...) # Constructor typically loads or lazy loads
            # Check existing stt_server logic: it calls load_model separately sometimes?
            # Let's assume constructor does setup or we call load_model.
            # Checking recent stt_server.py, engine init usually loads model.
            
            logger.info("SenseVoice Driver Loaded")
        except Exception as e:
            logger.error(f"Failed to load SenseVoice: {e}")
            raise e

    def transcribe(self, audio_data, **kwargs) -> str:
        if not self.engine:
            # Sync load if needed (warning: might block event loop if not careful, but transcribed usually in thread)
            # Since load is async, this method should strictly be called after load, or we hack sync load.
            raise RuntimeError("Driver not loaded")
            
        return self.engine.transcribe(audio_data)
