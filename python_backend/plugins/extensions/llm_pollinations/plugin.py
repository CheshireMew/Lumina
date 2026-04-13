from plugins.drivers.llm.pollinations_driver import PollinationsDriver
from services.managers.llm_driver_plugins import LLMDriverTypePlugin


class Plugin(LLMDriverTypePlugin):
    DRIVER_TYPE = "pollinations"
    DRIVER_CLASS = PollinationsDriver
    DISPLAY_NAME = "Pollinations"
    DESCRIPTION = "Registers the Pollinations free-tier LLM driver type."
