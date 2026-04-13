import logging
from typing import Any

from app_config import config
from core.interfaces.plugin import Plugin as BasePlugin

from .drivers.tts.edge_tts_driver import EdgeTTSDriver

logger = logging.getLogger("plugins.tts.edge")


class Plugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.driver = EdgeTTSDriver()

    async def enable(self):
        await super().enable()
        manager = self.context.get_service("tts")
        if not manager:
            logger.info("TTS manager not ready for %s", self.id)
            return

        self.driver.load_config(self.config)
        manager.drivers[self.id] = self.driver

        selected_provider = config.get_selected_provider("tts")
        if selected_provider == self.id or not getattr(manager, "active_driver", None):
            await manager.activate(self.id)

    async def disable(self):
        manager = self.context.get_service("tts")
        if manager:
            if getattr(manager, "active_driver_id", None) == self.id:
                await manager.disable_plugin(self.id)
            manager.drivers.pop(self.id, None)
        await super().disable()

    async def health(self) -> dict[str, Any]:
        manager = self.context.get_service("tts")
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
                "func_tag": "TTS",
                "config_schema": self.driver.config_schema or metadata.get("config_schema", {}),
            }
        )
        return metadata
