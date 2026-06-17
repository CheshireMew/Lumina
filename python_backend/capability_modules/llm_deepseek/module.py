from llm.drivers.deepseek_driver import DeepSeekDriver
from services.managers.llm_driver_plugins import LLMDriverTypeModule


class Capability(LLMDriverTypeModule):
    DRIVER_TYPE = "deepseek"
    DRIVER_CLASS = DeepSeekDriver
    DISPLAY_NAME = "DeepSeek"
    DESCRIPTION = "Registers the DeepSeek OpenAI-compatible LLM driver type."
