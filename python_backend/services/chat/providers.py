
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
            return await self._retrieve_memory(ctx)
        except Exception as e:
            logger.warning(f"RAG Provider failed: {e}")
            return None

    async def _retrieve_memory(self, ctx) -> Optional[str]:
        # 1. Extract Query
        user_text = ""
        for msg in reversed(ctx.original_messages):
            if msg.get("role") == "user":
                user_text = msg.get("content", "")
                break
        
        if not user_text or len(user_text) < 3: return None

        # 2. Embedding + Search
        # Note: Ideally moving embedding logic out, but maintaining functionality for now
        from model_manager import model_manager
        path = model_manager.ensure_embedding_model("all-MiniLM-L6-v2")
        emb_model = model_manager.load_embedding_model(path)
        
        vector = emb_model.encode(user_text).tolist()
        
        llm_manager = services.get_llm_manager()
        route = llm_manager.get_route("chat")
        
        # Default: Paid/Local Tier -> Episodic Memory (High Context)
        target_table = "episodic_memory"
        limit = 10
        min_results = 3
        
        # Free Tier -> Conversation Logs (Low Context)
        if route and route.provider_id == "free_tier":
            target_table = "conversation_log"
            limit = 3
            min_results = 1
        
        results = await services.surreal_system.search_hybrid(
            query=user_text,
            query_vector=vector,
            character_id=ctx.character_id,
            limit=limit,
            target_table=target_table,
            min_results=min_results
        )
        
        if results:
            content = "\n".join([f"- {r.get('content') or r.get('narrative', '')} ({r.get('created_at','')})" for r in results])
            # Set into context for pipeline to format consistently
            ctx.rag_context = content
            # Return None so it's not double-added via 'prompts' list
            return None
            
        return None


class SoulContextProvider(ContextProvider):
    """
    Renders personality and dynamic state (Short-Term Mood/State).
    """
    async def provide(self, ctx: Any) -> Optional[str]:
        if not services.soul:
            return None
            
        try:
            # Use unified get_system_prompt which handles fallback to config
            return await services.soul.get_system_prompt({'context': ctx})
            
        except Exception as e:
            logger.warning(f"Soul Provider failed: {e}")
            return "You are a helpful AI assistant."
