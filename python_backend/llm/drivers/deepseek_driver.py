import logging
from .openai_driver import OpenAIDriver

logger = logging.getLogger("DeepSeekDriver")

class DeepSeekDriver(OpenAIDriver):
    def __init__(self, id: str = "deepseek"):
        super().__init__(id, "DeepSeek Provider", "DeepSeek API (OpenAI Compatible)")
        
    async def load(self):
        # Set default DeepSeek URL if not present
        if self.config and not self.config.get("base_url"):
            self.config["base_url"] = "https://api.deepseek.com/v1"
            
        await super().load()
        logger.info("DeepSeekDriver loaded.")
