
import os
import logging
import threading
from typing import Dict, Optional, Any
from app_config import config as app_settings
from core.interfaces.driver import BaseSTTDriver

logger = logging.getLogger("STTManager")

# WHISPER_MODELS removed. Models are now dynamically discovered from drivers.

class STTPluginManager:
    def __init__(self):
        self.drivers: Dict[str, BaseSTTDriver] = {}
        self.active_driver_id: str = "driver.stt.sensevoice"
        self.active_driver: Optional[BaseSTTDriver] = None
        self.loading_status: str = "idle" 
        self.lock = threading.Lock()

    @property
    def current_model_name(self) -> str:
        return self.active_driver_id
        
    @property
    def engine_type(self) -> str:
        if self.active_driver_id == "driver.stt.sensevoice" or self.active_driver_id == "sense-voice": 
             return "sense_voice"
        if "plugin_asr" in self.active_driver_id: # Heuristic for generic plugins
             return "plugin_asr"
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
        self.loading_status = "loading" # [Status] Begin Transition
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
            self.active_driver_id = target_driver_id 
            self.active_driver = driver
            
            # 3. Notify frontend (optional, via WS)
            logger.info(f"Successfully switched to {driver_id}")
            
        except Exception as e:
            logger.error(f"Failed to switch driver {driver_id}: {e}", exc_info=True)
        finally:
            self.loading_status = "idle" # [Status] End Transition

    async def register_drivers(self, auto_activate: bool = True):
        # [Dynamic Loading]
        try:
            from services.plugins.loader import PluginLoader
            
            # Current: python_backend/services/stt_manager.py
            current_dir = os.path.dirname(os.path.abspath(__file__))
            
            # 1. Built-in Drivers: python_backend/plugins/drivers/stt
            # Navigate up from services/ to python_backend/ then down to plugins/drivers/stt
            backend_root = os.path.dirname(current_dir) # python_backend
            drivers_dir = os.path.join(backend_root, "plugins", "drivers", "stt")
            
            logger.info(f"Scanning Built-in STT Drivers: {drivers_dir}")
            if os.path.exists(drivers_dir):
                loaded_drivers = PluginLoader.load_plugins(drivers_dir, BaseSTTDriver)
                for driver in loaded_drivers:
                    self.drivers[driver.id] = driver
                    logger.info(f"[STT] Registered Driver: {driver.name} ({driver.id})")
            
            # 2. Extension Drivers: python_backend/plugins/extensions
            extensions_root = os.path.join(backend_root, "plugins", "extensions")
            
            if os.path.exists(extensions_root):
                for ext_name in os.listdir(extensions_root):
                    ext_drivers_dir = os.path.join(extensions_root, ext_name, "drivers", "stt")
                    if os.path.exists(ext_drivers_dir):
                        logger.info(f"Scanning Extension STT Drivers: {ext_drivers_dir}")
                        ext_loaded = PluginLoader.load_plugins(ext_drivers_dir, BaseSTTDriver)
                        for d in ext_loaded:
                             logger.info(f"[STT] 📦 Loaded Extension Driver from {ext_name}: {d.id} ({d.name})")
                             self.drivers[d.id] = d
                
        except Exception as e:
            logger.error(f"Failed to load dynamic STT drivers: {e}")
        
        # Load Config
        saved_provider = app_settings.stt.provider
        if not saved_provider or saved_provider not in self.drivers:
            # Fallback
            if "driver.stt.sensevoice" in self.drivers: saved_provider = "driver.stt.sensevoice"
            elif "sense-voice" in self.drivers: saved_provider = "sense-voice"
            elif "faster-whisper" in self.drivers: saved_provider = "faster-whisper"
            elif self.drivers: saved_provider = list(self.drivers.keys())[0]
            
        if saved_provider and auto_activate:
             if saved_provider in app_settings.plugins.disabled_plugins:
                 logger.info(f"🚫 Driver {saved_provider} is disabled in config. Skipping auto-activation.")
             else:
                 await self.activate(saved_provider)

    def register_driver(self, driver: BaseSTTDriver):
        """
        [Dynamic Registration]
        Called by stt_server.py when a plugin hot-loads a driver.
        """
        if not driver.id:
            logger.error("Cannot register driver without ID")
            return

        with self.lock:
            self.drivers[driver.id] = driver
            logger.info(f"✅ [STT] Dynamically Registered Driver: {driver.id}")
            
        # Optional: Auto-activate if it matches config?
        # For now, just register.

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

        # [Critical Fix] Avoid holding threading.Lock across await!
        with self.lock:
            if self.active_driver_id == driver_id and self.active_driver: return
            self.loading_status = "loading"
            
        try:
            logger.info(f"Activating STT Driver: {driver_id} (Background)")
            driver = self.drivers[driver_id]
            
            # Offload blocking load() to thread pool
            import asyncio
            loop = asyncio.get_running_loop()
            import inspect
            is_async = inspect.iscoroutinefunction(driver.load)
            
            if is_async:
                await driver.load()
            else:
                # Sync load wrapper
                logger.info(f"DEBUG: Running sync load for {driver_id}")
                await loop.run_in_executor(None, driver.load) # None uses default ThreadPoolExecutor
            
            # Update State (Re-acquire Lock)
            with self.lock:
                logger.info(f"DEBUG: Load finished for {driver_id}. Setting active driver.")
                self.active_driver = driver
                self.active_driver_id = driver_id
                logger.info(f"✅ Successfully activated {driver_id}")
        except Exception as e:
            logger.error(f"❌ Failed to activate driver {driver_id}: {e}", exc_info=True)
        finally:
            with self.lock:
                self.loading_status = "idle"

    async def unload_active_driver(self):
        """
        [Architecture 4.2] Force Unload.
        Called when the active plugin is disabled.
        """
        driver_to_unload = None
        driver_id = "none"
        
        with self.lock:
            if not self.active_driver:
                return
            
            driver_to_unload = self.active_driver
            driver_id = self.active_driver_id
            
            # Clear state BEFORE awaiting
            self.active_driver = None
            self.active_driver_id = "none"
            
        logger.info(f"🛑 Unloading Active Driver: {driver_id}")
        
        if hasattr(driver_to_unload, "unload"):
            try:
                import inspect
                if inspect.iscoroutinefunction(driver_to_unload.unload):
                    await driver_to_unload.unload()
                else:
                    driver_to_unload.unload()
            except Exception as e:
                logger.error(f"Error unloading driver {driver_id}: {e}")
        
        import gc
        gc.collect()

    # [Architecture 5.6] Bus Sync Interfaces
    async def enable_plugin(self, plugin_id: str):
        """Bridge for Lifecycle Bus"""
        await self.activate(plugin_id)

    async def disable_plugin(self, plugin_id: str):
        """Bridge for Lifecycle Bus"""
        if self.active_driver_id == plugin_id:
            await self.unload_active_driver()

    def transcribe(self, audio_data) -> Dict[str, Any]:
        with self.lock:
            if not self.active_driver: return {"text": ""}
            return self.active_driver.transcribe(audio_data)
