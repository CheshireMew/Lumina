
import logging
from typing import Dict, Optional
from pathlib import Path
from core.interfaces.driver import BaseTTSDriver
from core.runtime import runtime_target_for_capability
# from app_config import config as app_settings  # Removed global import

from .driver_loader import allow_extension_driver
from .provider_host import ProviderHostManager

logger = logging.getLogger("TTSManager")

class TTSPluginManager(ProviderHostManager):
    def __init__(self, config):
        super().__init__(config=config, capability="tts", default_driver_id="driver.tts.edge")

    async def register_drivers(self, auto_activate: bool = True):
        # Dynamic Loading via ProviderLoader
        try:
            from sdk.lumina.loader import PluginLoader
            
            base_dir = Path(__file__).resolve().parents[2]
            
            # 1. Built-in provider drivers
            drivers_dir = base_dir / "plugins" / "drivers" / "tts"
            if drivers_dir.exists():
                logger.info(f"Scanning Built-in TTS Drivers: {drivers_dir}")
                loaded = PluginLoader.load_plugins(str(drivers_dir), BaseTTSDriver)
                for d in loaded: self.drivers[d.id] = d
            
            # 2. Internal extension provider drivers
            extensions_root = base_dir / "plugins" / "extensions"
            
            if extensions_root.exists():
                logger.info(f"Scanning Extensions for TTS Drivers in: {extensions_root}")
                for ext_path in extensions_root.iterdir():
                    if ext_path.is_dir():
                         ext_drivers_dir = ext_path / "drivers" / "tts"
                         if ext_drivers_dir.exists():
                             allowed, manifest = allow_extension_driver(
                                 ext_path / "manifest.yaml",
                                 capability="tts",
                                 runtime_target=runtime_target_for_capability("tts"),
                             )
                             if not allowed:
                                 continue
                             logger.info(f"Scanning Extension Drivers: {ext_drivers_dir}")
                             ext_loaded = PluginLoader.load_plugins(str(ext_drivers_dir), BaseTTSDriver)
                             for d in ext_loaded:
                                 logger.info(f"📦 Loaded Extension Driver from {ext_path.name}: {d.id} ({d.name})")
                                 self.drivers[d.id] = d
            
        except Exception as e:
            logger.error(f"Failed to load dynamic TTS drivers: {e}")

        # Load Config
        saved_provider = self.config.get_selected_provider("tts")
        if not saved_provider or saved_provider not in self.drivers:
             # Fallback logic
             if "driver.tts.edge" in self.drivers: saved_provider = "driver.tts.edge"
             elif self.drivers: saved_provider = list(self.drivers.keys())[0]
        
        if saved_provider and auto_activate:
             if not self.config.is_plugin_desired_enabled(saved_provider):
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
        self.begin_transition(driver_id)
        
        try:
            driver = self.drivers[driver_id]
            import inspect
            if inspect.iscoroutinefunction(driver.load):
                await driver.load()
            else:
                driver.load()
            self.mark_ready(driver, driver_id)
        except Exception as e:
            logger.error(f"Failed to activate TTS driver {driver_id}: {e}")
            self.mark_error(str(e))
            self.active_driver_id = "none"
            raise

    async def unload_active_driver(self):
        """Standard Unload Implementation"""
        if not self.active_driver: return
        
        driver = self.active_driver
        driver_id = self.active_driver_id
        
        self.mark_unloaded()
        
        logger.info(f"🛑 Unloading TTS Driver: {driver_id}")
        if hasattr(driver, "unload"):
            import inspect
            if inspect.iscoroutinefunction(driver.unload):
                await driver.unload()
            else:
                driver.unload()
        
        import gc
        gc.collect()

    # [Architecture 5.6] Bus Sync Interfaces
    async def enable_plugin(self, plugin_id: str):
        await self.activate(plugin_id)

    async def disable_plugin(self, plugin_id: str):
        if self.active_driver_id == plugin_id:
            await self.unload_active_driver()
