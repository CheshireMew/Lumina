import logging
from dataclasses import dataclass
from typing import Any, Optional

from services.companion.context import CompanionContext

logger = logging.getLogger("CompanionInteractionRecorder")


@dataclass(frozen=True)
class CompanionInteraction:
    companion_context: CompanionContext
    user_message: str
    assistant_message: str
    user_name: Optional[str] = None
    companion_name: Optional[str] = None
    save_history: bool = True
    log_memory: bool = True
    update_soul_activity: bool = True
    notify_soul_driver: bool = True
    strict: bool = False


@dataclass(frozen=True)
class CompanionInteractionResult:
    memory_log_id: Optional[str] = None


class CompanionInteractionRecorder:
    """Single post-turn boundary for companion interaction side effects."""

    def __init__(
        self,
        *,
        memory_service: Any,
        session_manager: Any,
        soul_service: Any,
    ):
        if memory_service is None:
            raise ValueError("CompanionInteractionRecorder requires MemoryService")
        if session_manager is None:
            raise ValueError("CompanionInteractionRecorder requires SessionManager")
        if soul_service is None:
            raise ValueError("CompanionInteractionRecorder requires SoulService")

        self.memory_service = memory_service
        self.session_manager = session_manager
        self.soul_service = soul_service

    async def record(self, interaction: CompanionInteraction) -> CompanionInteractionResult:
        if not interaction.user_message and not interaction.assistant_message:
            return CompanionInteractionResult()

        if interaction.save_history:
            await self._save_turn_history(interaction)

        await self._record_soul_interaction(interaction)

        memory_log_id = None
        if interaction.log_memory:
            memory_log_id = await self._log_turn_to_memory(interaction)

        return CompanionInteractionResult(memory_log_id=memory_log_id)

    async def record_activity(self, *, strict: bool = False) -> None:
        soul_service = self.soul_service

        try:
            soul_service.update_last_interaction()
        except Exception as exc:
            logger.error("Failed to record companion activity: %s", exc)
            if strict:
                raise

    async def _save_turn_history(self, interaction: CompanionInteraction) -> None:
        session_manager = self.session_manager

        context = interaction.companion_context
        try:
            await session_manager.add_turn(
                context,
                interaction.user_message,
                interaction.assistant_message,
            )
        except Exception as exc:
            logger.error("Failed to save session history: %s", exc)
            if interaction.strict:
                raise

    async def _record_soul_interaction(self, interaction: CompanionInteraction) -> None:
        soul_service = self.soul_service

        context = interaction.companion_context
        try:
            if interaction.update_soul_activity:
                soul_service.update_last_interaction()

            if interaction.notify_soul_driver:
                await soul_service.on_interaction(
                    interaction.user_message,
                    interaction.assistant_message,
                    {
                        "session_id": context.session_id,
                        "user_id": context.user_id,
                        "character_id": context.character_id,
                    },
                )
        except Exception as exc:
            logger.error("Failed to record soul interaction: %s", exc)
            if interaction.strict:
                raise

    async def _log_turn_to_memory(self, interaction: CompanionInteraction) -> Optional[str]:
        memory_service = self.memory_service

        context = interaction.companion_context
        label = interaction.user_name or context.user_id
        companion_label = interaction.companion_name or context.character_id
        narrative = (
            f"{label}: {interaction.user_message or '(Silence)'}\n"
            f"{companion_label}: {interaction.assistant_message}"
        )
        try:
            log_id = await memory_service.log_conversation(context, narrative)
            logger.info("Conversation logged to memory")
            return str(log_id)
        except Exception as exc:
            logger.error("Failed to log conversation: %s", exc)
            if interaction.strict:
                raise
            return None
