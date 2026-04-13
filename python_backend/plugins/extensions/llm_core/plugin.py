from core.interfaces.plugin import Plugin as BasePlugin


class Plugin(BasePlugin):
    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "LLM Core",
                "description": "Core intelligence gateway for chat, tools and model routing.",
                "func_tag": "Kernel",
            }
        )
        return metadata
