from llm.drivers.pollinations_driver import PollinationsDriver
from services.managers.llm_driver_modules import LLMDriverTypeModule


class Capability(LLMDriverTypeModule):
    DRIVER_TYPE = "pollinations"
    DRIVER_CLASS = PollinationsDriver
    DISPLAY_NAME = "Pollinations"
    DESCRIPTION = "Registers the Pollinations free-tier LLM driver type."
