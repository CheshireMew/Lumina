import os
import json
import logging
from pathlib import Path
from typing import List, Dict, Any
from pydantic import BaseModel, Field

# Define SessionState locally since core.cognitive is missing
class SessionState(BaseModel):
    session_id: int = 0
    short_term_history: List[Dict[str, Any]] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

logger = logging.getLogger("SessionManager")

class SessionManager:
    def __init__(self, data_dir: str = "data/sessions"):
        self.data_dir = Path(data_dir)
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._cache = {} # Optional memory cache

    def _get_path(self, user_id: str, char_id: str) -> Path:
        # Sanitize IDs to avoid path traversal
        import re
        def sanitize(s):
            return re.sub(r'[^a-zA-Z0-9_\-]', '_', str(s)) or "default"
            
        u_id = sanitize(user_id) if user_id else "default_user"
        c_id = sanitize(char_id) if char_id else "default_char"
        return self.data_dir / f"{c_id}_{u_id}.json"

    def load_session(self, user_id: str, char_id: str) -> SessionState:
        """
        Loads the session state from disk.
        If file doesn't exist, returns a new (default) SessionState.
        """
        # [Optimization] Check Cache First
        cache_key = f"{user_id}:{char_id}"
        if cache_key in self._cache:
            return self._cache[cache_key]

        path = self._get_path(user_id, char_id)
        # logger.info(f"DEBUG: Loading Session from {path}") 
        
        state = None
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = SessionState(**data)
                logger.info(f"📂 Loaded Session {path}: {len(state.short_term_history)} turns")
            except Exception as e:
                logger.error(f"Failed to load session from {path}: {e}")
                state = SessionState(session_id=0) # Reset
        else:
            logger.info(f"No existing session for {user_id}:{char_id}, creating new at {path}")
            state = SessionState(session_id=0)
            
        # Cache Populate
        self._cache[cache_key] = state
        return state

    def save_session(self, user_id: str, char_id: str, state: SessionState):
        """
        Persists the session state to disk.
        """
        # [Optimization] Update Cache (Write-Through)
        cache_key = f"{user_id}:{char_id}"
        self._cache[cache_key] = state
        
        path = self._get_path(user_id, char_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save session to {path}: {e}")

    def clear_history(self, user_id: str, char_id: str):
        """Clear short-term history but keep session metadata"""
        # load first to preserve metadata
        state = self.load_session(user_id, char_id) 
        old_len = len(state.short_term_history)
        state.short_term_history = []
        self.save_session(user_id, char_id, state)
        logger.info(f"🧹 CLEARED HISTORY for {user_id}:{char_id} (Was {old_len} turns)")

    def clear_session(self, user_id: str, char_id: str):
        # [Optimization] Invalidate Cache
        cache_key = f"{user_id}:{char_id}"
        if cache_key in self._cache:
            del self._cache[cache_key]
            
        path = self._get_path(user_id, char_id)
        if path.exists():
            try:
                os.remove(path)
            except Exception as e:
                logger.error(f"Failed to delete session {path}: {e}")

    # --- Compatibility Methods (Legacy Support) ---
    def add_turn(self, user_id: str, char_id: str, user_msg: str, ai_msg: str):
        state = self.load_session(user_id, char_id)
        state.short_term_history.append({"role": "user", "content": user_msg})
        state.short_term_history.append({"role": "assistant", "content": ai_msg})
        
        # Limit history size based on Global Config
        from app_config import config
        limit = config.memory.history_limit
        strategy = config.memory.overflow_strategy
        
        # Override with defaults if invalid (though config should handle it)
        if limit <= 0: limit = 20
        
        if len(state.short_term_history) > limit:
            if strategy == "reset":
                 # Reset Strategy: Clear entire history when full
                 # (Optionally keep just the latest turn? User prompt says "Clear & Cache+" implying clear)
                 # We will clear it, effectively treating this turn as the LAST of the specific "Context Session".
                 # But wait, if we clear it, the NEXT turn starts fresh.
                 # The user might want the current turn to persist? 
                 # Usually "Reset Context" keeps the LATEST turn to start new context.
                 # Let's keep the last turn so the conversation continuity exists for the immediate reply, 
                 # but previous context is wiped.
                 state.short_term_history = state.short_term_history[-2:] 
                 logger.info(f"🔄 Context Overflow ({strategy}): Pruned history to last turn.")
            else:
                 # Slide Strategy (Default)
                 state.short_term_history = state.short_term_history[-limit:]
                 
        self.save_session(user_id, char_id, state)

    def get_history(self, user_id: str, char_id: str):
        state = self.load_session(user_id, char_id)
        return state.short_term_history

    def update_history(self, user_id: str, char_id: str, new_history: list):
        """Replace history with new list (e.g. after summarization)"""
        state = self.load_session(user_id, char_id)
        state.short_term_history = new_history
        self.save_session(user_id, char_id, state)

session_manager = SessionManager()

