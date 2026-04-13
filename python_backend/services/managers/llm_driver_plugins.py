from __future__ import annotations

from typing import Any, Type

from core.interfaces.driver import BaseLLMDriver
from core.interfaces.plugin import Plugin as BasePlugin


class LLMDriverTypePlugin(BasePlugin):
    DRIVER_TYPE = ""
    DRIVER_CLASS: Type[BaseLLMDriver]
    DISPLAY_NAME = ""
    DESCRIPTION = ""

    def create_driver(self, provider_id: str) -> BaseLLMDriver:
        return self.DRIVER_CLASS(id=provider_id)

    async def enable(self):
        await super().enable()
        llm_manager = self.context.get_service("llm_manager")
        if llm_manager is None:
            raise RuntimeError("LLMManager is not available for driver registration")

        llm_manager.register_driver_type(
            self.DRIVER_TYPE,
            self.create_driver,
            {
                "name": self.DISPLAY_NAME,
                "description": self.DESCRIPTION,
                "plugin_id": self.id,
            },
        )

    async def disable(self):
        llm_manager = self.context.get_service("llm_manager")
        if llm_manager:
            llm_manager.unregister_driver_type(self.DRIVER_TYPE)
        await super().disable()

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": self.DISPLAY_NAME,
                "description": self.DESCRIPTION,
                "provider_type": self.DRIVER_TYPE,
                "func_tag": "LLM",
            }
        )
        return metadata
