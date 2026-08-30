import asyncio
import logging
import uuid
from datetime import datetime, timezone
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
            from app_config import DATA_ROOT

            repo = FileSessionRepository(DATA_ROOT / "sessions")
        self.repo = repo
            
        self.config = config
        self._cache = {}
        self._locks: dict[str, asyncio.Lock] = {}

    def _cache_key(self, context: CompanionContext) -> str:
        return f"{context.user_id}:{context.character_id}"

    def _lock_for(self, context: CompanionContext) -> asyncio.Lock:
        return self._locks.setdefault(self._cache_key(context), asyncio.Lock())

    async def _load_session_unlocked(self, context: CompanionContext) -> SessionState:
        cache_key = self._cache_key(context)
        if cache_key in self._cache:
            return self._cache[cache_key]

        data = await self.repo.get_session(context.user_id, context.character_id)
        
        if data:
            try:
                state = SessionState(**data)
            except Exception as exc:
                raise RuntimeError(
                    f"Failed to parse session for {cache_key}: {exc}"
                ) from exc
        else:
            # logger.info(f"No existing session for {user_id}:{char_id}, creating new.")
            state = SessionState(session_id=0)
            
        self._cache[cache_key] = state
        return state

    async def load_session(self, context: CompanionContext) -> SessionState:
        """Load an isolated snapshot so callers cannot mutate cached state."""
        async with self._lock_for(context):
            state = await self._load_session_unlocked(context)
            return state.model_copy(deep=True)

    async def save_session(self, context: CompanionContext, state: SessionState):
        """
        Persists the session state (Async).
        """
        async with self._lock_for(context):
            await self._save_session_unlocked(context, state)

    async def _save_session_unlocked(
        self,
        context: CompanionContext,
        state: SessionState,
    ) -> None:
        cache_key = self._cache_key(context)
        snapshot = state.model_copy(deep=True)
        try:
            data = snapshot.model_dump()
            await self.repo.save_session(context.user_id, context.character_id, data)
        except Exception as exc:
            logger.error("Failed to save session %s: %s", cache_key, exc)
            raise
        self._cache[cache_key] = snapshot

    async def clear_history(self, context: CompanionContext):
        async with self._lock_for(context):
            state = await self._load_session_unlocked(context)
            old_len = len(state.short_term_history)
            candidate = state.model_copy(deep=True)
            candidate.short_term_history = []
            await self._save_session_unlocked(context, candidate)
        logger.info(
            f"🧹 CLEARED HISTORY for {context.user_id}:{context.character_id} "
            f"(Was {old_len} turns)"
        )

    async def clear_session(self, context: CompanionContext):
        async with self._lock_for(context):
            await self.repo.delete_session(context.user_id, context.character_id)
            self._cache.pop(self._cache_key(context), None)
    
    async def add_turn(
        self,
        context: CompanionContext,
        user_msg: str,
        ai_msg: str,
        *,
        turn_id: str | None = None,
        assistant_reasoning: str = "",
    ):
        limit = 20
        strategy = "slide"
        if self.config:
            limit = self.config.memory.history_limit
            strategy = self.config.memory.overflow_strategy
        if limit <= 0:
            limit = 20

        stable_turn_id = turn_id or str(uuid.uuid4())
        created_at = datetime.now(timezone.utc).isoformat()
        new_messages = [
            {
                "id": f"{stable_turn_id}:user",
                "turn_id": stable_turn_id,
                "role": "user",
                "content": user_msg,
                "created_at": created_at,
            },
            {
                "id": f"{stable_turn_id}:assistant",
                "turn_id": stable_turn_id,
                "role": "assistant",
                "content": ai_msg,
                "reasoning": assistant_reasoning,
                "created_at": created_at,
            },
        ]

        async with self._lock_for(context):
            state = await self._load_session_unlocked(context)
            candidate = state.model_copy(deep=True)
            existing_ids = {
                str(item.get("id"))
                for item in candidate.short_term_history
                if item.get("id")
            }
            candidate.short_term_history.extend(
                message for message in new_messages if message["id"] not in existing_ids
            )
            max_messages = limit * 2
            if len(candidate.short_term_history) > max_messages:
                if strategy == "reset":
                    candidate.short_term_history = new_messages
                else:
                    candidate.short_term_history = candidate.short_term_history[-max_messages:]
            await self._save_session_unlocked(context, candidate)

    async def get_history(self, context: CompanionContext):
        state = await self.load_session(context)
        return list(state.short_term_history)

    async def update_history(self, context: CompanionContext, new_history: list):
        async with self._lock_for(context):
            state = await self._load_session_unlocked(context)
            candidate = state.model_copy(deep=True)
            candidate.short_term_history = list(new_history)
            await self._save_session_unlocked(context, candidate)

