
import os
import logging
import threading
from typing import Dict, Optional, List
from app_config import config as app_settings
from core.interfaces.driver import BaseSTTDriver

logger = logging.getLogger("STTManager")

# WHISPER_MODELS removed. Models are now dynamically discovered from drivers.

class STTPluginManager:
    def __init__(self):
        self.drivers: Dict[str, BaseSTTDriver] = {}
        self.active_driver_id: str = "sense-voice"
        self.active_driver: Optional[BaseSTTDriver] = None
        self.loading_status: str = "idle" 
        self.lock = threading.Lock()

    @property
    def current_model_name(self) -> str:
        return self.active_driver_id
        
    @property
    def engine_type(self) -> str:
        if self.active_driver_id == "sense-voice": return "sense_voice"
        return "faster_whisper"

    @property
    def model(self):
        if self.active_driver:
            # Compatibility: SenseVoice uses .engine, Whisper uses .model
            if hasattr(self.active_driver, "engine") and self.active_driver.engine:
                 return self.active_driver.engine
            if hasattr(self.active_driver, "model") and self.active_driver.model:
                 return self.active_driver.model
        return None

    async def switch_model_background(self, driver_id: str):
        """Standard method for background switching"""
        
        target_driver_id = driver_id
        model_size_override = None

        # [Dynamic Model Discovery]
        # Iterate over all drivers to find who claims this model
        for d_id, drv in self.drivers.items():
            if hasattr(drv, "supported_models") and driver_id in drv.supported_models:
                 target_driver_id = d_id
                 model_size_override = driver_id
                 break
        
        if target_driver_id not in self.drivers:
            logger.error(f"Driver {target_driver_id} not found (Original request: {driver_id})")
            return

        logger.info(f"Switching to driver: {target_driver_id} (Model: {model_size_override or 'default'})")
        try:
            driver = self.drivers[target_driver_id]
            
            # Update Driver Config if needed
            if model_size_override:
                driver.config["model_size"] = model_size_override
                # Also Unload if strictly needed to force reload?
                if hasattr(driver, "model") and driver.model:
                    if hasattr(driver, "unload"):
                        await driver.unload()
                    else:
                        driver.model = None
                        import gc
                        gc.collect()

            # 1. Load the new driver
            await driver.load()
            
            # 2. Update active ID
            self.active_driver_id = driver_id 
            self.active_driver = driver
            
            # 3. Notify frontend (optional, via WS)
            logger.info(f"Successfully switched to {driver_id}")
            
        except Exception as e:
            logger.error(f"Failed to switch driver {driver_id}: {e}", exc_info=True)

    async def register_drivers(self, auto_activate: bool = True):
        # [Dynamic Loading]
        try:
            from services.plugin_loader import PluginLoader
            # Locate drivers relative to backend root or this file
            # This file is plugins/stt/manager.py
            # Backend root is ../../
            # Drivers are in plugins/drivers/stt
            
            # We need absolute path. self usually works.
            # But let's use the logic from stt_server but adapted.
            # stt_server using: os.path.dirname(...) + plugins/drivers/stt
            # Here: __file__ is .../plugins/stt/manager.py
            # Drivers: .../plugins/drivers/stt
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            drivers_dir = os.path.join(current_dir, "..", "drivers", "stt")
            # Or simplified: E:\Work\Code\Lumina\python_backend\plugins\drivers\stt
            
            # Adapting for plugins/stt/manager.py:
            # ../drivers/stt
            drivers_dir = os.path.abspath(os.path.join(current_dir, "..", "drivers", "stt"))
            
            if not os.path.exists(drivers_dir):
                # Try from root if structure is different
                drivers_dir = os.path.abspath(os.path.join(current_dir, "..", "..", "plugins", "drivers", "stt"))
            
            loaded_drivers = PluginLoader.load_plugins(drivers_dir, BaseSTTDriver)
            for driver in loaded_drivers:
                self.drivers[driver.id] = driver
                logger.info(f"[STT] Registered Dynamic Driver: {driver.name} ({driver.id})")
                
        except Exception as e:
            logger.error(f"Failed to load dynamic STT drivers: {e}")
        
        # Load Config
        saved_provider = app_settings.stt.provider
        if not saved_provider or saved_provider not in self.drivers:
            # Fallback
            if "sense-voice" in self.drivers: saved_provider = "sense-voice"
            elif "faster-whisper" in self.drivers: saved_provider = "faster-whisper"
            elif self.drivers: saved_provider = list(self.drivers.keys())[0]
            
        if saved_provider and auto_activate:
             await self.activate(saved_provider)

    async def activate(self, driver_id: str):
        if not self.drivers:
            logger.critical("No STT Drivers available! Service running in degraded mode.")
            self.loading_status = "idle"
            self.active_driver = None
            self.active_driver_id = "none"
            return

        if driver_id not in self.drivers: 
             logger.warning(f"Driver {driver_id} not found. available: {list(self.drivers.keys())}")
             driver_id = list(self.drivers.keys())[0]

        with self.lock:
            if self.active_driver_id == driver_id and self.active_driver: return
            
            self.loading_status = "loading"
            try:
                logger.info(f"Activating STT Driver: {driver_id}")
                driver = self.drivers[driver_id]
                await driver.load()
                self.active_driver = driver
                self.active_driver_id = driver_id
            finally:
                self.loading_status = "idle"

    def transcribe(self, audio_data) -> str:
        with self.lock:
            if not self.active_driver: return ""
            return self.active_driver.transcribe(audio_data)
