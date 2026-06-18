import asyncio
import inspect
import logging
import threading
from typing import Any, Dict, Optional

from capability_modules.stt_sensevoice.drivers.stt.sense_voice_driver import SenseVoiceDriver
from core.interfaces.driver import BaseSTTDriver

from .provider_host import ProviderHostManager

logger = logging.getLogger("STTManager")


class STTProviderManager(ProviderHostManager):
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
        if "provider_asr" in self.active_driver_id:
            return "provider_asr"
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

    async def load_drivers(self):
        self.register_driver(SenseVoiceDriver())

    async def activate_startup_driver(self):
        target_provider = self.resolve_startup_driver_id()
        if target_provider and self.config.is_provider_desired_enabled(target_provider):
            await self.activate(target_provider)

    async def register_drivers(self):
        await self.load_drivers()
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

    async def enable_provider(self, provider_id: str):
        await self.activate(provider_id)

    async def disable_provider(self, provider_id: str):
        if self.active_driver_id == provider_id:
            await self.unload_active_driver()

    def transcribe(self, audio_data) -> Dict[str, Any]:
        with self.lock:
            if self.active_driver is None:
                return {"text": ""}
            return self.active_driver.transcribe(audio_data)
