from llm.drivers.openai_driver import OpenAIDriver
from services.managers.llm_driver_modules import LLMDriverTypeModule


class Capability(LLMDriverTypeModule):
    DRIVER_TYPE = "openai"
    DRIVER_CLASS = OpenAIDriver
    DISPLAY_NAME = "OpenAI Compatible"
    DESCRIPTION = "Registers the standard OpenAI-compatible LLM driver type."
