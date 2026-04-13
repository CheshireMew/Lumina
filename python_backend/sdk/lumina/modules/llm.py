"""
LLM Module
==========

AI conversation functionality.

Example:
    response = await lumina.llm.chat("Hello")
    async for chunk in lumina.llm.stream("Tell me a story"):
        print(chunk.text)
"""

import logging
from typing import Optional, List, Dict, Any, AsyncIterator
from dataclasses import dataclass

from ..errors import DriverError
from ..utils import get_service_or_raise, driver_error_handler

logger = logging.getLogger("Lumina.SDK.LLM")


@dataclass
class ChatResponse:
    """Chat response"""
    text: str
    role: str = "assistant"
    model: str = ""
    usage: Dict[str, int] = None


@dataclass
class StreamChunk:
    """Streaming response chunk"""
    text: str
    is_final: bool = False


class LLMModule:
    """
    AI conversation module
    
    Methods:
        chat(message, **options) - Single turn conversation
        stream(message, **options) - Streaming conversation
    """
    
    def __init__(self, container):
        self._container = container
    
    def _get_llm_manager(self):
        """Get LLM manager or raise DriverError if unavailable."""
        return get_service_or_raise(self._container, 'llm', 'LLM')
    
    @driver_error_handler("LLM", "chat")
    async def chat(
        self,
        message: str,
        *,
        context: List[Dict[str, str]] = None,
        model: str = None,
        temperature: float = 0.7,
        max_tokens: int = None,
        timeout: float = 60.0,
        **kwargs
    ) -> ChatResponse:
        """
        Send chat message
        
        Args:
            message: User message
            context: Context message list [{"role": "user", "content": "..."}]
            model: Model name (optional, uses user config)
            temperature: Creativity (0.0-2.0)
            max_tokens: Maximum tokens
            timeout: Timeout in seconds
        
        Returns:
            Chat response
        
        Example:
            response = await lumina.llm.chat("Hello")
            print(response.text)
        """
        llm_manager = self._get_llm_manager()
        
        # Build message list
        messages = context or []
        messages.append({"role": "user", "content": message})
        
        # Build options
        options = {
            "temperature": temperature,
            **kwargs
        }
        if model:
            options["model"] = model
        if max_tokens:
            options["max_tokens"] = max_tokens
        
        if hasattr(llm_manager, 'chat'):
            result = await llm_manager.chat(messages, **options)
            if isinstance(result, str):
                return ChatResponse(text=result)
            return ChatResponse(
                text=result.get("content", result.get("text", str(result))),
                model=result.get("model", ""),
                usage=result.get("usage")
            )
        elif hasattr(llm_manager, 'generate'):
            text = await llm_manager.generate(message, **options)
            return ChatResponse(text=text)
        else:
            raise DriverError("LLM service does not support chat method")
    
    async def stream(
        self,
        message: str,
        *,
        context: List[Dict[str, str]] = None,
        model: str = None,
        temperature: float = 0.7,
        **kwargs
    ) -> AsyncIterator[StreamChunk]:
        """
        Streaming conversation
        
        Args:
            message: User message
            context: Context message list
            model: Model name
            temperature: Creativity
        
        Yields:
            Response chunks
        
        Example:
            async for chunk in lumina.llm.stream("Tell me a story"):
                print(chunk.text, end="")
        """
        llm_manager = self._get_llm_manager()
        
        try:
            messages = context or []
            messages.append({"role": "user", "content": message})
            
            options = {"temperature": temperature, **kwargs}
            if model:
                options["model"] = model
            
            if hasattr(llm_manager, 'stream'):
                async for chunk in llm_manager.stream(messages, **options):
                    if isinstance(chunk, str):
                        yield StreamChunk(text=chunk)
                    else:
                        yield StreamChunk(
                            text=chunk.get("content", chunk.get("text", "")),
                            is_final=chunk.get("is_final", False)
                        )
            else:
                # Fallback: non-streaming
                response = await self.chat(message, context=context, model=model, **kwargs)
                yield StreamChunk(text=response.text, is_final=True)
                
        except DriverError:
            raise
        except Exception as e:
            logger.error(f"LLM streaming call failed: {e}")
            raise DriverError(f"LLM streaming call failed: {e}")

