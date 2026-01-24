
import logging
from typing import Dict, Optional
from core.interfaces.driver import BaseTTSDriver
from app_config import config as app_settings
import os

logger = logging.getLogger("TTSManager")

class TTSPluginManager:
    def __init__(self):
        self.drivers: Dict[str, BaseTTSDriver] = {}
        self.active_driver_id: str = "driver.tts.edge"
        self.active_driver: Optional[BaseTTSDriver] = None
        self.loading_status: str = "idle" 

    async def register_drivers(self, auto_activate: bool = True):
        # Dynamic Loading via PluginLoader
        try:
            from services.plugins.loader import PluginLoader
            
            current_dir = os.path.dirname(os.path.abspath(__file__))
            # Navigate up to python_backend
            # capabilities/tts -> capabilities -> python_backend
            backend_root = os.path.dirname(os.path.dirname(current_dir)) 
            
            # 1. Built-in Drivers (Legacy: python_backend/plugins/drivers/tts)
            drivers_dir = os.path.join(backend_root, "plugins", "drivers", "tts")
            if os.path.exists(drivers_dir):
                logger.info(f"Scanning Built-in TTS Drivers: {drivers_dir}")
                loaded = PluginLoader.load_plugins(drivers_dir, BaseTTSDriver)
                for d in loaded: self.drivers[d.id] = d
            
            # 2. Extension Drivers (python_backend/plugins/extensions/*/drivers/tts)
            extensions_root = os.path.join(backend_root, "plugins", "extensions")
            
            if os.path.exists(extensions_root):
                logger.info(f"Scanning Extensions for TTS Drivers in: {extensions_root}")
                for ext_name in os.listdir(extensions_root):
                    ext_path = os.path.join(extensions_root, ext_name)
                    if os.path.isdir(ext_path):
                         ext_drivers_dir = os.path.join(ext_path, "drivers", "tts")
                         if os.path.exists(ext_drivers_dir):
                             logger.info(f"Scanning Extension Drivers: {ext_drivers_dir}")
                             ext_loaded = PluginLoader.load_plugins(ext_drivers_dir, BaseTTSDriver)
                             for d in ext_loaded:
                                 logger.info(f"📦 Loaded Extension Driver from {ext_name}: {d.id} ({d.name})")
                                 self.drivers[d.id] = d
            
        except Exception as e:
            logger.error(f"Failed to load dynamic TTS drivers: {e}")

        # Load Config
        saved_provider = app_settings.tts.provider 
        if not saved_provider or saved_provider not in self.drivers:
             # Fallback logic
             if "driver.tts.edge" in self.drivers: saved_provider = "driver.tts.edge"
             elif self.drivers: saved_provider = list(self.drivers.keys())[0]
        
        if saved_provider and auto_activate:
             if saved_provider in app_settings.plugins.disabled_plugins:
                 logger.info(f"🚫 Driver {saved_provider} is disabled in config. Skipping auto-activation.")
             else:
                 await self.activate(saved_provider)

    async def activate(self, driver_id: str):
        if not self.drivers:
            logger.critical("No TTS Drivers available! Service running in degraded mode.")
            self.active_driver = None
            self.active_driver_id = "none"
            return

        if driver_id not in self.drivers:
            # Fallback to the first available driver
            fallback = list(self.drivers.keys())[0]
            logger.warning(f"Driver {driver_id} not found, falling back to {fallback}")
            driver_id = fallback
            
        logger.info(f"Activating TTS Driver: {driver_id}")
        self.loading_status = "loading"
        
        try:
            driver = self.drivers[driver_id]
            import inspect
            if inspect.iscoroutinefunction(driver.load):
                await driver.load()
            else:
                driver.load()
            self.active_driver = driver
            self.active_driver_id = driver_id
        except Exception as e:
            logger.error(f"Failed to activate TTS driver {driver_id}: {e}")
            self.active_driver = None
            self.active_driver_id = "none"
        finally:
            self.loading_status = "idle"

    async def unload_active_driver(self):
        """Standard Unload Implementation"""
        if not self.active_driver: return
        
        driver = self.active_driver
        driver_id = self.active_driver_id
        
        self.active_driver = None
        self.active_driver_id = "none"
        
        logger.info(f"🛑 Unloading TTS Driver: {driver_id}")
        if hasattr(driver, "unload"):
            import inspect
            if inspect.iscoroutinefunction(driver.unload):
                await driver.unload()
            else:
                driver.unload()
        
        import gc
        gc.collect()

    async def enable_plugin(self, plugin_id: str):
        await self.activate(plugin_id)

    async def disable_plugin(self, plugin_id: str):
        if self.active_driver_id == plugin_id:
            await self.unload_active_driver()
