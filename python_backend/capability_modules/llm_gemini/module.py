from llm.drivers.gemini_driver import GeminiDriver
from services.managers.llm_driver_plugins import LLMDriverTypeModule


class Capability(LLMDriverTypeModule):
    DRIVER_TYPE = "gemini"
    DRIVER_CLASS = GeminiDriver
    DISPLAY_NAME = "Gemini"
    DESCRIPTION = "Registers the Gemini OpenAI-compatible LLM driver type."
