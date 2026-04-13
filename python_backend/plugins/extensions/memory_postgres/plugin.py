import logging
from typing import Any

from app_config import config
from core.interfaces.plugin import Plugin as BasePlugin
from memory.factory import MemoryDriverFactory

logger = logging.getLogger("plugins.memory.postgres")


class Plugin(BasePlugin):
    async def enable(self):
        await super().enable()
        memory_service = self.context.get_service("memory")
        if not memory_service:
            return

        selected_provider = config.get_selected_provider("memory")
        if selected_provider != self.id:
            return

        current_driver = getattr(memory_service, "driver", None)
        if current_driver and getattr(current_driver, "id", None) == self.id:
            return

        try:
            next_driver = MemoryDriverFactory.create_driver(config_provider=self.id)
            await next_driver.connect()
        except Exception as exc:
            logger.error("Memory backend %s is unavailable: %s", self.id, exc)
            return

        if current_driver and hasattr(current_driver, "close"):
            await current_driver.close()

        memory_service.driver = next_driver
        memory_service.vector_store.driver = next_driver
        if hasattr(memory_service, "set_available"):
            memory_service.set_available(True)
        logger.info("Memory backend switched to %s", self.id)

    async def disable(self):
        memory_service = self.context.get_service("memory")
        if memory_service:
            current_driver = getattr(memory_service, "driver", None)
            if current_driver and getattr(current_driver, "id", None) == self.id:
                logger.warning("Active memory backend %s was disabled; runtime will keep current connection until another provider is selected.", self.id)
        await super().disable()

    async def health(self) -> dict[str, Any]:
        memory_service = self.context.get_service("memory")
        current_driver = getattr(memory_service, "driver", None) if memory_service else None
        is_active = bool(current_driver and getattr(current_driver, "id", None) == self.id)
        selected_provider = config.get_selected_provider("memory")
        if selected_provider == self.id and not is_active:
            status = "error"
        else:
            status = "ready" if is_active else ("disabled" if not self.enabled else "idle")
        return {
            "status": status,
            "active": is_active,
            "driver_id": getattr(current_driver, "id", None),
        }

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "PostgreSQL Memory",
                "description": "PostgreSQL + pgvector memory backend exposed as a formal memory provider plugin.",
                "func_tag": "Memory",
            }
        )
        return metadata
