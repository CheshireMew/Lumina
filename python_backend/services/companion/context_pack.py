import asyncio
import logging
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from services.companion.context import CompanionContext

logger = logging.getLogger("CompanionContextPack")


@dataclass(frozen=True)
class CompanionContextPack:
    """Single prompt-context boundary for one companion turn."""

    identity: CompanionContext
    user_message: str
    recent_session_history: List[Dict[str, Any]] = field(default_factory=list)
    relevant_memories: str = ""
    stable_profile_facts: str = ""
    current_soul_state: Dict[str, Any] = field(default_factory=dict)
    runtime_capabilities: Dict[str, Any] = field(default_factory=dict)
    current_time: str = ""
    system_prompt: str = ""

    def prompt_sections(self) -> List[str]:
        sections: List[str] = []
        if self.relevant_memories:
            sections.append(
                "## Relevant Memories\n"
                f"{self.relevant_memories}"
            )
        if self.stable_profile_facts:
            sections.append(
                "## Stable User Profile\n"
                f"{self.stable_profile_facts}"
            )
        if self.current_soul_state:
            sections.append(
                "## Companion State\n"
                f"{self.current_soul_state}"
            )
        if self.runtime_capabilities:
            sections.append(
                "## Runtime Capabilities\n"
                f"{self.runtime_capabilities}"
            )
        if self.current_time:
            sections.append(f"## Current Time\n{self.current_time}")
        return sections


class CompanionContextPackBuilder:
    """Builds all dynamic prompt context before chat pipeline execution."""

    def __init__(
        self,
        *,
        session_manager: Any,
        memory_service: Any,
        soul_service: Any,
        config: Any = None,
    ):
        if session_manager is None:
            raise ValueError("CompanionContextPackBuilder requires SessionManager")
        if memory_service is None:
            raise ValueError("CompanionContextPackBuilder requires MemoryService")
        if soul_service is None:
            raise ValueError("CompanionContextPackBuilder requires SoulService")

        self.session_manager = session_manager
        self.memory_service = memory_service
        self.soul_service = soul_service
        self.config = config

    async def build(
        self,
        *,
        companion_context: CompanionContext,
        user_message: str,
        history_limit: int,
        enable_memory: bool = True,
    ) -> CompanionContextPack:
        if not isinstance(companion_context, CompanionContext):
            raise ValueError("CompanionContextPackBuilder requires CompanionContext")

        memory_request = (
            self._relevant_memories(
                companion_context,
                user_message,
            )
            if enable_memory
            else asyncio.sleep(0, result="")
        )
        history, memories, system_prompt = await asyncio.gather(
            self._recent_session_history(companion_context, history_limit),
            memory_request,
            self.soul_service.get_system_prompt(
                {
                    "companion_context": companion_context,
                    "context_pack": "companion_turn",
                }
            ),
        )

        return CompanionContextPack(
            identity=companion_context,
            user_message=user_message,
            recent_session_history=history,
            relevant_memories=memories,
            current_soul_state=self._soul_state(),
            runtime_capabilities=self._runtime_capabilities(),
            current_time=datetime.now(timezone.utc).isoformat(),
            system_prompt=system_prompt,
        )

    async def _recent_session_history(
        self,
        companion_context: CompanionContext,
        history_limit: int,
    ) -> List[Dict[str, Any]]:
        state = await self.session_manager.load_session(companion_context)
        history = getattr(state, "short_term_history", []) or []
        return [
            {"role": item["role"], "content": item["content"]}
            for item in history[-(history_limit * 2):]
            if item.get("role") and item.get("content")
        ]

    async def _relevant_memories(
        self,
        companion_context: CompanionContext,
        user_message: str,
    ) -> str:
        if not user_message or len(user_message.strip()) < 3:
            return ""
        return await self.memory_service.retrieve_context(
            query=user_message,
            context=companion_context,
            limit=10,
        )

    def _soul_state(self) -> Dict[str, Any]:
        active_character = None
        try:
            active_character = self.soul_service.get_active_character_id()
        except Exception:
            logger.debug("Soul service does not expose active character state")

        if not active_character:
            return {}
        return {"active_character_id": active_character}

    def _runtime_capabilities(self) -> Dict[str, Any]:
        config = self.config
        capabilities = getattr(config, "capabilities", None)
        selected = getattr(capabilities, "selected_providers", None)
        if not selected:
            return {}
        return {"selected_providers": dict(selected)}
