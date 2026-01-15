import os
import json
import logging
from typing import Optional
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
        path = self._get_path(user_id, char_id)
        
        if path.exists():
            try:
                with open(path, "r", encoding="utf-8") as f:
                    data = json.load(f)
                state = SessionState(**data)
                # logger.info(f"Loaded session for {user_id}:{char_id}")
                return state
            except Exception as e:
                logger.error(f"Failed to load session from {path}: {e}")
                # Fallback to new session on error (or raise?)
                return SessionState(session_id=0) # Reset
        else:
            logger.info(f"No existing session for {user_id}:{char_id}, creating new.")
            return SessionState(session_id=0)

    def save_session(self, user_id: str, char_id: str, state: SessionState):
        """
        Persists the session state to disk.
        """
        path = self._get_path(user_id, char_id)
        try:
            with open(path, "w", encoding="utf-8") as f:
                f.write(state.model_dump_json(indent=2))
        except Exception as e:
            logger.error(f"Failed to save session to {path}: {e}")

    def clear_history(self, user_id: str, char_id: str):
        """Clear short-term history but keep session metadata"""
        state = self.load_session(user_id, char_id)
        state.short_term_history = []
        self.save_session(user_id, char_id, state)

    def clear_session(self, user_id: str, char_id: str):
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
        # Limit history size
        if len(state.short_term_history) > 40: # default threshold
            state.short_term_history = state.short_term_history[-40:]
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

