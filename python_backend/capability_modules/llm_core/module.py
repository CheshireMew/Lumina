from core.interfaces.module import CapabilityModule


class Capability(CapabilityModule):
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
