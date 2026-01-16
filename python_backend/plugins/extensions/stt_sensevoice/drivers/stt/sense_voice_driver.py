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

    def load(self):
        """
        Synchronous load (CPU heavy). 
        STTPluginManager wraps this in run_in_executor.
        """
        if self.engine: return
        try:
            # Ensure we can import from root if needed
            # 1. Add 'python_backend' folder (which contains 'plugins') to sys.path
            backend_path = os.path.join(os.getcwd(), "python_backend")
            if backend_path not in sys.path:
                sys.path.append(backend_path)
            
            # Ensure Root Directory is in sys.path to allow 'from python_backend...' imports
            root_dir = os.path.dirname(backend_path)
            if root_dir not in sys.path:
                sys.path.insert(0, root_dir)

            # 3. Import Engine
            # 3. Import Engine
            try:
                # Try relative import (Standard in Micro-Kernel)
                from .sensevoice.engine import SenseVoiceEngine
            except ImportError:
                # Fallback: Dynamic load from file (If package context is missing)
                # This is normal when loaded via generic PluginLoader which might not set __package__
                # logger.debug("Relative import failed. Attempting dynamic load from file.")
                import importlib.util
                engine_path = os.path.join(os.path.dirname(__file__), "sensevoice", "engine.py")
                if not os.path.exists(engine_path):
                    raise FileNotFoundError(f"SenseVoice engine not found at {engine_path}")
                
                spec = importlib.util.spec_from_file_location("sensevoice_engine", engine_path)
                mod = importlib.util.module_from_spec(spec)
                sys.modules["sensevoice_engine"] = mod 
                spec.loader.exec_module(mod)
                SenseVoiceEngine = mod.SenseVoiceEngine
            
            # We assume model path is managed by app_config or passed here.
            # For now, let the engine handle its internal paths as before.
            self.engine = SenseVoiceEngine()
            
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
