import logging
from .openai_driver import OpenAIDriver

logger = logging.getLogger("GeminiDriver")

class GeminiDriver(OpenAIDriver):
    """
    Gemini Driver using Google's OpenAI-compatible API.
    Docs: https://ai.google.dev/gemini-api/docs/openai
    """
    def __init__(self):
        super().__init__("gemini", "Gemini Provider", "Google Gemini API (OpenAI Compatible)")
        
    async def load(self):
        # Set default Gemini OpenAI-Compatible URL if not present
        if self.config and not self.config.get("base_url"):
            self.config["base_url"] = "https://generativelanguage.googleapis.com/v1beta/openai/"
            
        await super().load()
        logger.info("GeminiDriver loaded.")
