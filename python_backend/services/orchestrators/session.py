import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from core.interfaces.repository import ISessionRepository
from services.companion.context import CompanionContext
from services.repositories.file_session_repository import FileSessionRepository

# Define SessionState locally since core.cognitive is missing
class SessionState(BaseModel):
    session_id: int = 0
    short_term_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

logger = logging.getLogger("SessionManager")

class SessionManager:
    def __init__(self, repo: Optional[ISessionRepository] = None, config=None):
        if repo is None:
            from app_config import BASE_DIR

            repo = FileSessionRepository(BASE_DIR / "data" / "sessions")
        self.repo = repo
            
        self.config = config
        self._cache = {}

    def _cache_key(self, context: CompanionContext) -> str:
        return f"{context.user_id}:{context.character_id}"

    async def load_session(self, context: CompanionContext) -> SessionState:
        """
        Loads the session state from repository (Async).
        """
        # [Optimization] Check Cache First (In-Memory L1)
        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = await self.repo.get_session(context.user_id, context.character_id)
        
        if data:
            try:
                state = SessionState(**data)
                # logger.info(f"📂 Loaded Session: {len(state.short_term_history)} turns")
            except Exception as e:
                logger.error(f"Failed to parse session data: {e}")
                state = SessionState(session_id=0)
        else:
            # logger.info(f"No existing session for {user_id}:{char_id}, creating new.")
            state = SessionState(session_id=0)
            
        # Cache Populate
        self._cache[cache_key] = state
        return state

    async def save_session(self, context: CompanionContext, state: SessionState):
        """
        Persists the session state (Async).
        """
        # [Optimization] Update Cache
        cache_key = self._cache_key(context)
        self._cache[cache_key] = state
        
        try:
            data = state.model_dump()
            await self.repo.save_session(context.user_id, context.character_id, data)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")
            raise

    async def clear_history(self, context: CompanionContext):
        state = await self.load_session(context)
        old_len = len(state.short_term_history)
        state.short_term_history = []
        await self.save_session(context, state)
        logger.info(
            f"🧹 CLEARED HISTORY for {context.user_id}:{context.character_id} "
            f"(Was {old_len} turns)"
        )

    async def clear_session(self, context: CompanionContext):
        # [Optimization] Invalidate Cache
        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            del self._cache[cache_key]
            
        await self.repo.delete_session(context.user_id, context.character_id)
    
    async def add_turn(self, context: CompanionContext, user_msg: str, ai_msg: str):
        state = await self.load_session(context)
        state.short_term_history.append({"role": "user", "content": user_msg})
        state.short_term_history.append({"role": "assistant", "content": ai_msg})
        
        limit = 20
        strategy = "slide"
        
        if self.config:
            limit = self.config.memory.history_limit
            strategy = self.config.memory.overflow_strategy
        if limit <= 0: limit = 20
        
        if len(state.short_term_history) > limit:
            if strategy == "reset":
                 keep_count = limit
                 state.short_term_history = state.short_term_history[-keep_count:] 
                 logger.info(f"🔄 Context Overflow ({strategy}): Pruned history to last {keep_count} turns.")
            else:
                 state.short_term_history = state.short_term_history[-limit:]
                 
        await self.save_session(context, state)

    async def get_history(self, context: CompanionContext):
        state = await self.load_session(context)
        return state.short_term_history

    async def update_history(self, context: CompanionContext, new_history: list):
        state = await self.load_session(context)
        state.short_term_history = new_history
        await self.save_session(context, state)

