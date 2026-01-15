from plugins.base import BaseSystemPlugin

class LLMManagerPlugin(BaseSystemPlugin):
    @property
    def id(self) -> str:
        return "llm-manager"

    @property
    def name(self) -> str:
        return "LLM Intelligence"

    @property
    def category(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return "Manage AI Models (DeepSeek, Free Tier, OpenAI). Configure API Keys and Routes."

    @property
    def enabled(self) -> bool:
        return True

    @property
    def active_in_group(self) -> bool:
        return False

    @property
    def config_schema(self):
        return {"type": "llm_manager"}

    @property
    def func_tag(self) -> str:
        return "Intelligence"

    def initialize(self, context):
        pass
