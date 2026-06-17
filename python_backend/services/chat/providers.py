from typing import Optional, Any
from core.interfaces.context import ContextProvider


class RAGContextProvider(ContextProvider):
    """
    Retrieves execution-time memories (Long-Term Memory).
    """
    def __init__(self, services_container):
        self.services = services_container

    async def provide(self, ctx: Any) -> Optional[str]:
        if not ctx.enable_rag:
            return None

        return await self._retrieve_memory(ctx)

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
            context=ctx.companion_context,
            limit=10,
        )
        if rag_context:
            ctx.rag_context = rag_context
            return None

        return None
