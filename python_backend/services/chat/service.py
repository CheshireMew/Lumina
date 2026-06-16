import logging
from typing import Any, AsyncGenerator, Dict, List, Optional

logger = logging.getLogger("ChatTurnService")


class ChatTurnService:
    """Single orchestration boundary for all chat entry points."""

    def __init__(
        self,
        *,
        pipeline: Any,
        memory_service: Any = None,
        session_manager: Any = None,
        soul_service: Any = None,
    ):
        self.pipeline = pipeline
        self.memory_service = memory_service
        self.session_manager = session_manager
        self.soul_service = soul_service

    def active_character_id(self, fallback: str = "hiyori") -> str:
        soul = self.soul_service
        if soul and hasattr(soul, "get_active_character_id"):
            return soul.get_active_character_id()
        return fallback

    async def build_turn_messages(
        self,
        user_id: str,
        character_id: str,
        text: str,
        history_limit: int = 10,
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        session_manager = self.session_manager
        if session_manager:
            try:
                state = await session_manager.load_session(user_id, character_id)
                history = getattr(state, "short_term_history", []) or []
                messages.extend(
                    {"role": item["role"], "content": item["content"]}
                    for item in history[-history_limit:]
                    if item.get("role") and item.get("content")
                )
            except Exception as exc:
                logger.error("Failed to load session for chat turn: %s", exc)

        messages.append({"role": "user", "content": text})
        return messages

    async def stream_response(
        self,
        *,
        messages: List[Dict[str, Any]],
        user_id: str,
        character_id: str,
        model: Optional[str] = None,
        temperature: float = 0.7,
        enable_rag: bool = True,
        enable_tools: bool = True,
        save_history: bool = True,
        log_memory: bool = True,
        user_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        final_response = ""
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        async for token in self.pipeline.run(
            messages,
            user_id=user_id,
            character_id=character_id,
            stream=True,
            model=model,
            temperature=temperature,
            enable_rag=enable_rag,
            enable_tools=enable_tools,
            save_history=save_history,
        ):
            final_response += token
            yield token

        if log_memory and user_msg and final_response:
            await self.log_turn_to_memory(
                user_id=user_id,
                character_id=character_id,
                user_message=user_msg,
                assistant_message=final_response,
                user_name=user_name,
            )

    async def collect_response(self, **kwargs) -> str:
        content = ""
        async for token in self.stream_response(**kwargs):
            content += token
        return content

    async def log_turn_to_memory(
        self,
        *,
        user_id: str,
        character_id: str,
        user_message: str,
        assistant_message: str,
        user_name: Optional[str] = None,
    ) -> None:
        memory_service = self.memory_service
        if not memory_service:
            return

        label = user_name or user_id
        narrative = f"{label}: {user_message}\n{character_id}: {assistant_message}"
        try:
            await memory_service.log_conversation(character_id, narrative)
            logger.info("Conversation logged to memory")
        except Exception as exc:
            logger.error("Failed to log conversation: %s", exc)
