import asyncio
import inspect
import logging
import os
import threading
from pathlib import Path
from typing import Any, Dict, Optional

from core.interfaces.driver import BaseSTTDriver
from core.runtime import runtime_target_for_capability

from .driver_loader import DriverPluginLoader, allow_extension_driver
from .provider_host import ProviderHostManager

logger = logging.getLogger("STTManager")


class STTPluginManager(ProviderHostManager):
    def __init__(self, config):
        super().__init__(config=config, capability="stt")
        self.lock = threading.Lock()

    @property
    def current_model_name(self) -> str:
        return self.active_driver_id

    @property
    def engine_type(self) -> str:
        if self.active_driver_id in {"driver.stt.sensevoice", "sense-voice"}:
            return "sense_voice"
        if "plugin_asr" in self.active_driver_id:
            return "plugin_asr"
        return "faster_whisper"

    @property
    def model(self):
        if self.active_driver:
            return self.active_driver.current_model
        return None

    async def switch_model_background(self, driver_id: str):
        target_driver_id = driver_id
        model_size_override = None

        for discovered_id, driver in self.drivers.items():
            if driver.supports_model(driver_id):
                target_driver_id = discovered_id
                model_size_override = driver_id
                break

        if target_driver_id not in self.drivers:
            raise ValueError(f"Unknown STT provider: {driver_id}")

        self.begin_transition(target_driver_id)
        try:
            driver = self.drivers[target_driver_id]
            if model_size_override:
                await self._select_driver_model(driver, model_size_override)

            await self._load_driver(driver)
            with self.lock:
                self.mark_ready(driver, target_driver_id)
            logger.info("STT provider switched to %s", target_driver_id)
        except Exception as exc:
            self.mark_error(str(exc))
            logger.error("Failed to switch STT provider %s: %s", driver_id, exc, exc_info=True)
            raise

    async def load_driver_plugins(self):
        try:
            base_dir = os.path.dirname(
                os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            )
            drivers_dir = os.path.join(base_dir, "plugins", "drivers", "stt")
            if os.path.exists(drivers_dir):
                loaded = DriverPluginLoader.load_plugins(drivers_dir, BaseSTTDriver)
                for driver in loaded:
                    self.register_driver(driver)

            extensions_root = os.path.join(base_dir, "plugins", "extensions")
            if os.path.exists(extensions_root):
                for ext_name in os.listdir(extensions_root):
                    ext_drivers_dir = os.path.join(extensions_root, ext_name, "drivers", "stt")
                    if os.path.exists(ext_drivers_dir):
                        manifest_path = os.path.join(extensions_root, ext_name, "manifest.yaml")
                        allowed, manifest = allow_extension_driver(
                            Path(manifest_path),
                            capability="stt",
                            runtime_target=runtime_target_for_capability("stt"),
                        )
                        if not allowed:
                            continue
                        loaded = DriverPluginLoader.load_plugins(ext_drivers_dir, BaseSTTDriver)
                        for driver in loaded:
                            self.register_driver(driver)
        except Exception as exc:
            logger.error("Failed to load STT drivers: %s", exc)

    async def activate_startup_driver(self):
        target_provider = self.resolve_startup_driver_id()
        if target_provider and self.config.is_plugin_desired_enabled(target_provider):
            await self.activate(target_provider)

    async def register_drivers(self):
        await self.load_driver_plugins()
        await self.activate_startup_driver()

    def register_driver(self, driver: BaseSTTDriver):
        with self.lock:
            super().register_driver(driver)

    def unregister_driver(self, driver_id: str) -> Any:
        with self.lock:
            return super().unregister_driver(driver_id)

    async def activate(self, driver_id: str):
        if not self.drivers:
            self.mark_error("No STT drivers available")
            self.active_driver_id = "none"
            return

        if driver_id not in self.drivers:
            self.mark_error(f"Unknown STT provider: {driver_id}")
            raise ValueError(f"Unknown STT provider: {driver_id}")

        with self.lock:
            if self.active_driver_id == driver_id and self.active_driver is not None:
                return
            self.begin_transition(driver_id)

        try:
            driver = self.drivers[driver_id]
            await self._load_driver(driver)
            with self.lock:
                self.mark_ready(driver, driver_id)
            logger.info("Activated STT provider %s", driver_id)
        except Exception as exc:
            with self.lock:
                self.mark_error(str(exc))
                self.active_driver_id = "none"
            logger.error("Failed to activate STT provider %s: %s", driver_id, exc, exc_info=True)
            raise

    async def _load_driver(self, driver: BaseSTTDriver):
        loop = asyncio.get_running_loop()
        if inspect.iscoroutinefunction(driver.load):
            await driver.load()
        else:
            await loop.run_in_executor(None, driver.load)

    async def _select_driver_model(self, driver: BaseSTTDriver, model_id: str):
        selected = driver.select_model(model_id)
        if inspect.isawaitable(selected):
            await selected

    async def unload_active_driver(self):
        driver_to_unload: Optional[BaseSTTDriver] = None
        driver_id = "none"
        with self.lock:
            if self.active_driver is None:
                return
            driver_to_unload = self.active_driver
            driver_id = self.active_driver_id
            self.mark_unloaded()

        logger.info("Unloading STT provider %s", driver_id)
        try:
            unloaded = driver_to_unload.unload()
            if inspect.isawaitable(unloaded):
                await unloaded
        except Exception as exc:
            logger.error("Error unloading STT provider %s: %s", driver_id, exc)

    async def enable_plugin(self, plugin_id: str):
        await self.activate(plugin_id)

    async def disable_plugin(self, plugin_id: str):
        if self.active_driver_id == plugin_id:
            await self.unload_active_driver()

    def transcribe(self, audio_data) -> Dict[str, Any]:
        with self.lock:
            if self.active_driver is None:
                return {"text": ""}
            return self.active_driver.transcribe(audio_data)
