from plugins.base import BaseSystemPlugin

class LLMCorePlugin(BaseSystemPlugin):
    """
    Unified LLM Core Plugin.
    This plugin represents the LLM Subsystem in the Plugin Store.
    It doesn't implement the drivers (which are now core/built-in),
    but it serves as the interface for ensuring the subsystem is active.
    """
    @property
    def id(self) -> str:
        return "system.llm_core"

    @property
    def name(self) -> str:
        return "LLM Core"

    @property
    def category(self) -> str:
        return "system"

    @property
    def description(self) -> str:
        return "Core Intelligence Module. Manages connection to AI models (DeepSeek, OpenAI, Gemini, Pollinations) and conversation routing."

    @property
    def config_schema(self):
        # Pointing to the special 'llm_manager' schema type that the frontend understands
        # or defining specific fields if we want the generic config editor to work.
        # For now, let's keep it simple or reuse the 'llm_manager' type if frontend supports it.
        # But 'llm_manager' type in frontend (LLMConfigModal) is triggered by the Neural Link button usually.
        return {"type": "llm_settings_link"} 

    def initialize(self, context):
        # We could inspect loaded drivers here to report status
        pass
