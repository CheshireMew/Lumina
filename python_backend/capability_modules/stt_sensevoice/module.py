import logging
from typing import Any

from core.interfaces.module import CapabilityModule

from .drivers.stt.sense_voice_driver import SenseVoiceDriver

logger = logging.getLogger("capability_modules.stt.sensevoice")


class Capability(CapabilityModule):
    def __init__(self):
        super().__init__()
        self.driver = SenseVoiceDriver()

    async def enable(self):
        await super().enable()
        manager = self.context.get_service("stt")
        if not manager:
            logger.info("STT manager not ready for %s", self.id)
            return

        self.driver.load_config(self.config)
        manager.register_driver(self.driver)

        config = self.context.get_service("config")
        selected_provider = config.get_selected_provider("stt")
        if selected_provider == self.id:
            await manager.activate(self.id)

    async def disable(self):
        manager = self.context.get_service("stt")
        if manager:
            if manager.active_driver_id == self.id:
                await manager.disable_provider(self.id)
            manager.unregister_driver(self.id)
        await super().disable()

    async def health(self) -> dict[str, Any]:
        manager = self.context.get_service("stt")
        is_active = bool(manager and manager.active_driver_id == self.id)
        return {
            "status": "ready" if is_active else ("disabled" if not self.enabled else "idle"),
            "active": is_active,
            "driver_id": self.driver.id,
        }

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": self.driver.name,
                "description": self.driver.description,
                "func_tag": "STT",
                "config_schema": self.driver.config_schema or metadata.get("config_schema", {}),
            }
        )
        return metadata
