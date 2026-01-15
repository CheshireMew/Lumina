import logging
import asyncio
from typing import List, Dict, Any, AsyncGenerator, Optional
from services.container import services
# from llm.manager import llm_manager
from services.session_manager import session_manager
from fastapi import HTTPException

logger = logging.getLogger("ChatService")

class ChatService:
    def __init__(self):
        pass
        
    async def chat_stream(
        self, 
        messages: Optional[List[Dict[str, str]]] = None, 
        user_name: str = "User",
        char_name: str = "Assistant", 
        role_override: str = "user",
        long_term_memory: str = "",
        user_input: Optional[str] = None, # Direct Input
        user_id: str = "default_user",
        character_id: str = "default_char"
    ) -> AsyncGenerator[str, None]:
        if messages is None:
            messages = []
            
        """
        Unified Chat Stream Logic.
        Assembles: System Prompt + RAG + History + User Message
        """
        soul = services.soul_client
        if not soul:
            logger.error("Soul Client not ready")
            yield "System Error: Soul Client not initialized"
            return

        # 1. Get Driver
        try:
            llm_manager = services.get_llm_manager()
            driver = await llm_manager.get_driver("chat")
        except Exception as e:
            logger.error(f"Failed to get chat driver: {e}")
            yield f"System Error: {str(e)}"
            return
            
        # 2. Get Dynamic Params
        FEATURE = "chat"
        # Force refresh profile via direct access if needed, or rely on soul_client state
        # params = await llm_manager.get_parameters(FEATURE, soul_state=...) 
        # Using the router's logic helper or direct call:
        # We need to construct the soul_state dict here if we want dynamic params.
        
        soul_state = None
        if soul.config.get("soul_evolution_enabled", True):
             soul_state = {
                "pad": soul.profile.get("personality", {}).get("pad_model", {}),
                "energy": soul.profile.get("state", {}).get("energy_level", 100),
                "rel_level": soul.profile.get("relationship", {}).get("level", 0)
             }
             
        params = llm_manager.get_parameters(FEATURE, soul_state=soul_state)
        model_name = llm_manager.get_model_name(FEATURE)

        # Server-Side Context Management
        full_response = ""
        is_server_side = False
        final_messages = []
        
        if user_input:
            is_server_side = True
            # 1. RAG Retrieval
            rag_context = long_term_memory # Fallback to arg if provided
            if not rag_context and services.surreal_system:
                try:
                    # [HOTFIX] Ensure Embedding Model is loaded & generate vector
                    if not hasattr(llm_manager, "embedding_model") or llm_manager.embedding_model is None:
                         # Lazy load via model_manager (Global import to avoid circular dep?)
                         from model_manager import model_manager
                         model_path = model_manager.ensure_embedding_model("all-MiniLM-L6-v2") # Standardize this later
                         llm_manager.embedding_model = model_manager.load_embedding_model(str(model_path))

                    vector = None
                    if llm_manager.embedding_model:
                         vector = llm_manager.embedding_model.encode(user_input).tolist()

                    # Try hybrid search first
                    if vector:
                        results = await services.surreal_system.search_hybrid(
                            query=user_input, 
                            vector=vector,  
                            limit=3, 
                            character_id=character_id
                        )
                        if results:
                            rag_context = "\n".join([r['content'] for r in results])
                    else:
                        logger.warning("RAG Skipped: No embedding model available.")

                except Exception as e:
                    logger.warning(f"RAG Search failed: {e}")

            # 2. Build Prompt (System + Context + History + User)
            # A. System
            final_messages.append({"role": "system", "content": soul.get_system_prompt({"user_name": user_name})})
            
            # B. Context
            if rag_context:
                final_messages.append({"role": "system", "content": f"## Related Memories\n{rag_context}"})
                
            # C. History (Session)
            session_history = session_manager.get_history(user_id, character_id)
            
            # [Configurable History Limit]
            # 1. Get user config or default
            history_limit = int(params.get("history_limit", 20))
            overflow_strategy = params.get("overflow_strategy", "slide") # Default to slide
            
            # 2. Check for Free Tier (Force strict limit)
            route = llm_manager.get_route(FEATURE)
            if route and route.provider_id == "free_tier":
                 history_limit = 5 # Strict limit for free tier
                 logger.info(f"🔒 Free Tier Detected: Enforcing history limit = {history_limit}")

            # 3. Apply Overflow Strategy
            if len(session_history) >= history_limit:
                 if overflow_strategy == "reset":
                     # [Strategy: Reset]
                     # Clear history (simulating archive/dreaming handoff) and start fresh.
                     # This preserves Prefix Cache stability for the previous N turns.
                     logger.info(f"🌊 Overflow Reset Triggered (Limit {history_limit}). Clearing Session History.")
                     session_manager.clear_history(user_id, character_id)
                     session_history = [] 
                     # Note: We do NOT create a summary here synchronously. 
                     # The assumption is Dreaming runs periodically or we trigger it async.
                     # If we want to trigger generic archival, we could:
                     # asyncio.create_task(self._archive_session(user_id, character_id, ...))
                 else:
                     # [Strategy: Slide] (Default)
                     # Standard FIFO
                     session_history = session_history[-history_limit:]
                 
            final_messages.extend(session_history)
            
            # D. User Input
            # If role_override is 'user', simply add it? 
            # Actually, session history does NOT include current turn yet.
            final_messages.append({"role": role_override, "content": user_input})
            
        else:
            # [Legacy Mode] Client Managed
            system_prompt = soul.get_system_prompt(user_context={"user_name": user_name})
            
            # Check for existing system prompt
            has_system = False
            for m in messages:
                if m.get("role") == "system":
                    has_system = True
                    # Optional: Override content? For now trust client or prepend/append.
                    break
            
            if not has_system:
                 final_messages.append({"role": "system", "content": system_prompt})

            if long_term_memory:
                 final_messages.append({"role": "system", "content": f"## 鐩稿叧璁板繂\n{long_term_memory}"})
                 
            final_messages.extend(messages)
        
        logger.info(f"[Chat] Streaming with {model_name} (Temp: {params.get('temperature')})")
        
        try:
            # 4. Stream
            # Driver expects: messages, model, **kwargs
            async_gen = await driver.chat_completion(
                final_messages,
                model=model_name,
                stream=True,
                **params
            )
            
            async for chunk in async_gen:
                if is_server_side:
                    full_response += chunk
                yield chunk
            
            # Update History
            if is_server_side:
                session_manager.add_turn(user_id, character_id, user_input, full_response)
                # Background Summarization Check
                # If history gets too long (> 20 messages), trigger summarization
                hist_len = len(session_manager.get_history(user_id, character_id))
                if hist_len > 20:
                     asyncio.create_task(self._summarize_session(user_id, character_id, soul, model_name))

        except Exception as e:
            logger.error(f"Streaming error: {e}", exc_info=True)
            yield f"[Error: {str(e)}]"

    async def _summarize_session(self, user_id: str, char_id: str, soul: Any, model: str):
        """
        Compress session history to prevent context window overflow.
        Uses a separate LLM call to summarize old messages.
        """
        try:
             history = session_manager.get_history(user_id, char_id)
             if len(history) < 20: return
             
             # Slice old messages (keep last 10)
             to_summarize = history[:-10]
             keep_messages = history[-10:]
             
             context_text = "\n".join([f"{m['role']}: {m['content']}" for m in to_summarize])
             
             prompt = [
                 {"role": "system", "content": "You are a memory compressor. Summarize the following conversation segment into a single concise paragraph. Keep key facts."},
                 {"role": "user", "content": context_text}
             ]
             
             # We need a non-streaming driver call
             llm_manager = services.get_llm_manager()
             driver = await llm_manager.get_driver("chat")
             summary = await driver.chat_completion(prompt, model=model, stream=False)
             
             if summary:
                 # Clean summary
                 summary_text = str(summary).strip()
                 logger.info(f"馃攧 Compressed {len(to_summarize)} messages into summary.")
                 
                 # Update Session Manager: Replace old messages with Summary
                 # SessionManager API might need update to support 'set_history' or we manually construct
                 # Note: SessionManager is ephemeral or persistent? it's in-memory + json.
                 # Let's verify session_manager API. For now, we update in-place if possible.
                 session_manager.update_history(user_id, char_id, 
                     [{"role": "system", "content": f"## Previous Summary\n{summary_text}"}] + keep_messages
                 )

        except Exception as e:
            logger.error(f"Session Summarization Failed: {e}")

chat_service = ChatService()
