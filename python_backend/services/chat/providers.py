
import logging
from typing import Optional, Any
from core.interfaces.context import ContextProvider

logger = logging.getLogger("ContextProviders")

class RAGContextProvider(ContextProvider):
    """
    Retrieves execution-time memories (Long-Term Memory).
    """
    def __init__(self, services_container):
        self.services = services_container

    async def provide(self, ctx: Any) -> Optional[str]:
        if not ctx.enable_rag:
            return None

        try:
            return await self._retrieve_memory(ctx)
        except Exception as e:
            logger.warning(f"RAG Provider failed: {e}")
            return None

    async def _retrieve_memory(self, ctx) -> Optional[str]:
        user_text = ""
        for msg in reversed(ctx.original_messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break
        
        if not user_text or len(user_text) < 3:
            return None

        memory = self.services.get_memory()
        rag_context = await memory.retrieve_context(
            query=user_text,
            character_id=ctx.character_id,
            limit=10,
        )
        if rag_context:
            ctx.rag_context = rag_context
            return None

        return None


class SoulContextProvider(ContextProvider):
    """
    Renders personality and dynamic state (Short-Term Mood/State).
    """
    def __init__(self, services_container):
        self.services = services_container

    async def provide(self, ctx: Any) -> Optional[str]:
        if not self.services.soul:
            return None
            
        try:
            # Use unified get_system_prompt which handles fallback to config
            return await self.services.soul.get_system_prompt({'context': ctx})
            
        except Exception as e:
            logger.warning(f"Soul Provider failed: {e}")
            return "You are a helpful AI assistant."
