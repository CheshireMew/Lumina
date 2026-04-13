import logging
from typing import Any

from app_config import config
from core.interfaces.plugin import Plugin as BasePlugin

from .drivers.stt.sense_voice_driver import SenseVoiceDriver

logger = logging.getLogger("plugins.stt.sensevoice")


class Plugin(BasePlugin):
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

        selected_provider = config.get_selected_provider("stt")
        if selected_provider == self.id or not getattr(manager, "active_driver", None):
            await manager.activate(self.id)

    async def disable(self):
        manager = self.context.get_service("stt")
        if manager:
            if getattr(manager, "active_driver_id", None) == self.id:
                await manager.disable_plugin(self.id)
            manager.drivers.pop(self.id, None)
        await super().disable()

    async def health(self) -> dict[str, Any]:
        manager = self.context.get_service("stt")
        is_active = bool(manager and getattr(manager, "active_driver_id", None) == self.id)
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
