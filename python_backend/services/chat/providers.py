
import logging
from typing import Optional, Any
from core.interfaces.context import ContextProvider
from services.container import services

logger = logging.getLogger("ContextProviders")

class RAGContextProvider(ContextProvider):
    """
    Retrieves execution-time memories (Long-Term Memory).
    """
    async def provide(self, ctx: Any) -> Optional[str]:
        if not ctx.enable_rag or not services.surreal_system:
            return None
            
        try:
            return await self._retrieve_memory(ctx.original_messages, ctx.character_id)
        except Exception as e:
            logger.warning(f"RAG Provider failed: {e}")
            return None

    async def _retrieve_memory(self, messages, character_id) -> str:
        # 1. Extract Query
        user_text = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break
        
        if not user_text or len(user_text) < 3: return ""

        # 2. Embedding + Search
        # Note: Ideally moving embedding logic out, but maintaining functionality for now
        from model_manager import model_manager
        path = model_manager.ensure_embedding_model("all-MiniLM-L6-v2")
        emb_model = model_manager.load_embedding_model(path)
        
        vector = emb_model.encode(user_text).tolist()
        
        results = await services.surreal_system.search_hybrid(
            query=user_text,
            query_vector=vector,
            character_id=character_id,
            limit=5
        )
        
        if results:
            content = "\n".join([f"- {r.get('content','')} ({r.get('created_at','')})" for r in results])
            return f"## Relevant Memories\n{content}"
            
        return ""


class SoulContextProvider(ContextProvider):
    """
    Renders personality and dynamic state (Short-Term Mood/State).
    """
    async def provide(self, ctx: Any) -> Optional[str]:
        if not services.soul_client:
            return None
            
        try:
            # 1. Static Prompt
            static = services.soul_client.render_static_prompt()
            
            # 2. Dynamic Instruction
            dynamic = services.soul_client.render_dynamic_instruction()
            
            # Combine
            final = static
            if dynamic:
                final += f"\n\n{dynamic}"
            return final
            
        except Exception as e:
            logger.warning(f"Soul Provider failed: {e}")
            return "You are a helpful AI assistant."
