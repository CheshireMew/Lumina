import logging

from core.interfaces.plugin import Plugin as BasePlugin


class Plugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self._logger = logging.getLogger("HelloWidget")

    async def enable(self):
        await super().enable()
        await self.context.emit(
            "ui:register_widget",
            {
                "id": "hello_clock",
                "plugin_id": self.id,
                "src": f"/api/plugins/{self.id}/assets/index.html",
                "location": "sidebar_right",
                "title": "Stock Clock",
                "height": "160px",
            },
        )

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "Hello Widget",
                "description": "Registers a simple sidebar clock widget for frontend integration checks.",
                "func_tag": "Widget",
            }
        )
        return metadata
