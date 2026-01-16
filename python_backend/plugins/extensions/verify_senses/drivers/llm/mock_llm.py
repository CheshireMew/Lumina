from core.interfaces.driver import BaseLLMDriver
from typing import AsyncGenerator, List, Dict
import logging

logger = logging.getLogger("MockLLM")

class MockLLMDriver(BaseLLMDriver):
    def __init__(self, id: str = "mock-llm"):
         super().__init__(id=id, name="Mock LLM (Extension)")
         self.config = {}

    def load_config(self, config: Dict):
        self.config = config
        
    async def load(self):
        pass

    async def list_models(self) -> List:
        return ["mock-gpt-4"]
        
    async def chat_completion(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        yield "Hello! I am a Mock LLM loaded from an extension."
