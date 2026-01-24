import logging
from openai import AsyncOpenAI
from typing import Any, Optional
from core.interfaces.driver import BaseLLMDriver

logger = logging.getLogger("OpenAIDriver")

class OpenAIDriver(BaseLLMDriver):
    def __init__(self, id: str = "openai", name: str = "OpenAI Provider", description: str = "Standard OpenAI-compatible API"):
        super().__init__(id, name, description)
        self.client: Optional[AsyncOpenAI] = None
        
    async def load(self):
        # Config should be loaded via load_config before load()
        # Expecting 'base_url', 'api_key' in config
        if not self.config:
             logger.warning("OpenAIDriver loaded without config.")
             return
             
        self.client = AsyncOpenAI(
            base_url=self.config.get("base_url"),
            api_key=self.config.get("api_key"),
            timeout=self.config.get("timeout", 60.0),
            max_retries=self.config.get("max_retries", 2)
        )
        logger.info(f"OpenAIDriver initialized with BaseURL: {self.config.get('base_url')}")

    async def chat_completion(self, 
                            messages: list, 
                            model: str, 
                            temperature: float = 0.7, 
                            stream: bool = False,
                            **kwargs) -> Any:
        if not self.client:
            await self.load() # Lazy load if needed
            
        try:
            # Map known kwargs or pass through
            # Make sure top_p etc are handled
            response = await self.client.chat.completions.create(
                model=model,
                messages=messages,
                temperature=temperature,
                stream=stream,
                **kwargs
            )
            
            if stream:
                async def stream_generator():
                    # [Fix] Stream Processing: Extract CONTENT only.
                    # Do NOT yield raw objects, because Pipeline/Frontend might serialize them fully,
                    # revealing internal fields like 'reasoning_content' or full JSON structure.
                    async for chunk in response:
                        if not chunk.choices: continue
                        delta = chunk.choices[0].delta
                        
                        # 1. Extract Main Content
                        content = delta.content or ""
                        
                        # 2. Extract Reasoning (DeepSeek-R1 style)
                        reasoning = getattr(delta, "reasoning_content", "") or ""
                        
                        # Yield structured data so Pipeline can decide what to log vs stream
                        if content or reasoning:
                            yield {"content": content, "reasoning": reasoning}
                return stream_generator()
            else:
                # Return content string
                return response.choices[0].message.content
        except Exception as e:
            logger.error(f"OpenAI Chat Completion Error: {e}")
            raise

    async def list_models(self) -> list:
        if not self.client:
             await self.load()
        try:
             models = await self.client.models.list()
             return [m.id for m in models.data]
        except Exception as e:
             logger.warning(f"Failed to list models: {e}")
             return []
