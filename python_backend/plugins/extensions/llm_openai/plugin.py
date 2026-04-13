from plugins.drivers.llm.openai_driver import OpenAIDriver
from services.managers.llm_driver_plugins import LLMDriverTypePlugin


class Plugin(LLMDriverTypePlugin):
    DRIVER_TYPE = "openai"
    DRIVER_CLASS = OpenAIDriver
    DISPLAY_NAME = "OpenAI Compatible"
    DESCRIPTION = "Registers the standard OpenAI-compatible LLM driver type."
