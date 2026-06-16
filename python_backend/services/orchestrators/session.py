import logging
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from pathlib import Path
from core.interfaces.repository import ISessionRepository
from services.repositories.file_session_repository import FileSessionRepository

# Define SessionState locally since core.cognitive is missing
class SessionState(BaseModel):
    session_id: int = 0
    short_term_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

logger = logging.getLogger("SessionManager")

class SessionManager:
    def __init__(self, repo: ISessionRepository = None, config=None, data_dir: str = "data/sessions"):
        # Compatibility: Allow data_dir arg but use it to init default repo if needed
        if repo:
            self.repo = repo
        else:
            # Default to File Repo
            from app_config import BASE_DIR
            root = Path(data_dir) if data_dir else BASE_DIR / "data" / "sessions"
            self.repo = FileSessionRepository(root)
            
        self.config = config
        self._cache = {} # keeping memory cache for now, though Repo could handle it.

    async def load_session(self, user_id: str, char_id: str) -> SessionState:
        """
        Loads the session state from repository (Async).
        """
        # [Optimization] Check Cache First (In-Memory L1)
        cache_key = f"{user_id}:{char_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        # Repo Access
        # Note: We rely on FileSessionRepository's get_by_composite_id extension for now
        # Ideally we should strictly use `get(id)` if we standardized IDs.
        data = None
        if hasattr(self.repo, "get_by_composite_id"):
             data = await self.repo.get_by_composite_id(user_id, char_id)
        
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

    async def save_session(self, user_id: str, char_id: str, state: SessionState):
        """
        Persists the session state (Async).
        """
        # [Optimization] Update Cache
        cache_key = f"{user_id}:{char_id}"
        self._cache[cache_key] = state
        
        try:
            data = state.model_dump()
            if hasattr(self.repo, "save_by_composite_id"):
                await self.repo.save_by_composite_id(user_id, char_id, data)
        except Exception as e:
            logger.error(f"Failed to save session: {e}")

    async def clear_history(self, user_id: str, char_id: str):
        state = await self.load_session(user_id, char_id) 
        old_len = len(state.short_term_history)
        state.short_term_history = []
        await self.save_session(user_id, char_id, state)
        logger.info(f"🧹 CLEARED HISTORY for {user_id}:{char_id} (Was {old_len} turns)")

    async def clear_session(self, user_id: str, char_id: str):
        # [Optimization] Invalidate Cache
        cache_key = f"{user_id}:{char_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            
        # Repository Delete
        # We need to derive ID or use composite method
        # FileRepo uses {c}_{u} pattern
        # This is leaky abstraction but acceptable for Phase 1.
        import re
        u_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(user_id)) or "default_user"
        c_id = re.sub(r'[^a-zA-Z0-9_\-]', '_', str(char_id)) or "hiyori"
        composite_id = f"{c_id}_{u_id}"
        
        await self.repo.delete(composite_id)

    # --- Async Compatibility Methods ---
    
    async def add_turn(self, user_id: str, char_id: str, user_msg: str, ai_msg: str):
        state = await self.load_session(user_id, char_id)
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
                 keep_count = max(4, limit // 2)
                 state.short_term_history = state.short_term_history[-keep_count:] 
                 logger.info(f"🔄 Context Overflow ({strategy}): Pruned history to last {keep_count} turns.")
            else:
                 state.short_term_history = state.short_term_history[-limit:]
                 
        await self.save_session(user_id, char_id, state)

    async def get_history(self, user_id: str, char_id: str):
        state = await self.load_session(user_id, char_id)
        return state.short_term_history

    async def update_history(self, user_id: str, char_id: str, new_history: list):
        state = await self.load_session(user_id, char_id)
        state.short_term_history = new_history
        await self.save_session(user_id, char_id, state)

# Instantiate with default (will use FileRepo)
session_manager = SessionManager()

