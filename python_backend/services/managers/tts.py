
import logging
import inspect
import gc
from pathlib import Path
from core.interfaces.driver import BaseTTSDriver
from core.runtime import runtime_target_for_capability

from .driver_loader import DriverLoader, allow_extension_driver
from .provider_host import ProviderHostManager

logger = logging.getLogger("TTSManager")

class TTSPluginManager(ProviderHostManager):
    def __init__(self, config):
        super().__init__(config=config, capability="tts")

    async def load_drivers(self):
        # Dynamic loading via DriverLoader.
        try:
            base_dir = Path(__file__).resolve().parents[2]

            modules_root = base_dir / "capability_modules"

            if modules_root.exists():
                logger.info(f"Scanning capability modules for TTS drivers in: {modules_root}")
                for ext_path in modules_root.iterdir():
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
                             ext_loaded = DriverLoader.load_plugins(str(ext_drivers_dir), BaseTTSDriver)
                             for d in ext_loaded:
                                 logger.info(f"📦 Loaded Extension Driver from {ext_path.name}: {d.id} ({d.name})")
                                 self.register_driver(d)
            
        except Exception as e:
            logger.error(f"Failed to load dynamic TTS drivers: {e}")

    async def activate_startup_driver(self):
        target_provider = self.resolve_startup_driver_id()
        if target_provider:
            if not self.config.is_provider_desired_enabled(target_provider):
                logger.info(f"🚫 Driver {target_provider} is disabled in config. Skipping auto-activation.")
            else:
                await self.activate(target_provider)

    async def register_drivers(self):
        await self.load_drivers()
        await self.activate_startup_driver()

    async def activate(self, driver_id: str):
        if not self.drivers:
            logger.critical("No TTS Drivers available! Service running in degraded mode.")
            self.active_driver = None
            self.active_driver_id = "none"
            return

        if driver_id not in self.drivers:
            self.mark_error(f"Unknown TTS provider: {driver_id}")
            raise ValueError(f"Unknown TTS provider: {driver_id}")
            
        logger.info(f"Activating TTS Driver: {driver_id}")
        self.begin_transition(driver_id)
        
        try:
            driver = self.drivers[driver_id]
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
        unloaded = driver.unload()
        if inspect.isawaitable(unloaded):
            await unloaded
        
        gc.collect()

    async def enable_provider(self, provider_id: str):
        await self.activate(provider_id)

    async def disable_provider(self, provider_id: str):
        if self.active_driver_id == provider_id:
            await self.unload_active_driver()

    def resolve_driver(self, engine: str):
        if self.has_driver(engine):
            return self.require_driver(engine)
        prefixed = f"driver.tts.{engine}"
        if self.has_driver(prefixed):
            return self.require_driver(prefixed)
        raise ValueError(f"Unknown TTS provider: {engine}")
