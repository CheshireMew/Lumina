import asyncio
import logging
import uuid
from dataclasses import dataclass, replace
from typing import Any, Optional

from services.companion.context import CompanionContext
from services.companion.post_turn_journal import POST_TURN_STEPS, PostTurnJournal

logger = logging.getLogger("CompanionInteractionRecorder")


@dataclass(frozen=True)
class CompanionInteraction:
    companion_context: CompanionContext
    user_message: str
    assistant_message: str
    turn_id: Optional[str] = None
    assistant_reasoning: str = ""
    user_name: Optional[str] = None
    companion_name: Optional[str] = None
    save_history: bool = True
    log_memory: bool = True
    update_soul_activity: bool = True
    notify_soul_driver: bool = True
    strict: bool = False


@dataclass(frozen=True)
class CompanionInteractionResult:
    turn_id: Optional[str] = None
    pending_steps: tuple[str, ...] = ()


class CompanionInteractionRecorder:
    """Single post-turn boundary for companion interaction side effects."""

    def __init__(
        self,
        *,
        memory_service: Any,
        session_manager: Any,
        soul_service: Any,
        journal: PostTurnJournal | None = None,
        consolidation_service: Any = None,
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
        self.journal = journal
        self.consolidation_service = consolidation_service
        self._tasks: set[asyncio.Task] = set()
        self._tasks_by_turn: dict[str, asyncio.Task] = {}
        self._closing = False

    async def record(self, interaction: CompanionInteraction) -> CompanionInteractionResult:
        if interaction.turn_id:
            existing = self._tasks_by_turn.get(str(interaction.turn_id))
            if existing and not existing.done():
                return await asyncio.shield(existing)
        prepared = await self._prepare(interaction)
        if prepared is None:
            return CompanionInteractionResult()
        stable, state = prepared
        return await self._record_stable(stable, state)

    async def schedule(self, interaction: CompanionInteraction) -> CompanionInteractionResult:
        """Durably accept a post-turn operation, then finish it outside response delivery."""
        if self._closing:
            return await self.record(interaction)
        if interaction.turn_id:
            existing = self._tasks_by_turn.get(str(interaction.turn_id))
            if existing and not existing.done():
                return CompanionInteractionResult(turn_id=str(interaction.turn_id))
        prepared = await self._prepare(interaction)
        if prepared is None:
            return CompanionInteractionResult()
        stable, state = prepared
        if state.get("status") == "completed":
            return CompanionInteractionResult(turn_id=stable.turn_id)
        task = asyncio.create_task(
            self._record_stable(stable, state),
            name=f"post-turn:{stable.turn_id}",
        )
        self._tasks.add(task)
        self._tasks_by_turn[str(stable.turn_id)] = task
        task.add_done_callback(self._post_turn_done)
        return CompanionInteractionResult(turn_id=stable.turn_id)

    async def close(self) -> None:
        self._closing = True
        if self._tasks:
            await asyncio.gather(*tuple(self._tasks), return_exceptions=True)
        if self.journal is not None:
            await self.journal.close()

    def _post_turn_done(self, task: asyncio.Task) -> None:
        self._tasks.discard(task)
        for turn_id, current in tuple(self._tasks_by_turn.items()):
            if current is task:
                self._tasks_by_turn.pop(turn_id, None)
                break
        if task.cancelled():
            logger.warning("Post-turn task was cancelled before completion")
            return
        error = task.exception()
        if error:
            logger.error("Post-turn task failed: %s", error)

    async def _prepare(
        self,
        interaction: CompanionInteraction,
    ) -> tuple[CompanionInteraction, dict[str, Any]] | None:
        if not interaction.user_message and not interaction.assistant_message:
            return None

        stable = interaction if interaction.turn_id else replace(
            interaction,
            turn_id=str(uuid.uuid4()),
        )
        state = await self._begin(stable)
        return stable, state

    async def _record_stable(
        self,
        stable: CompanionInteraction,
        state: dict[str, Any],
    ) -> CompanionInteractionResult:
        if state.get("status") == "completed":
            return CompanionInteractionResult(turn_id=stable.turn_id)

        operations = (
            ("history", stable.save_history, self._save_turn_history),
            ("memory", stable.log_memory, self._record_turn),
            ("soul_activity", stable.update_soul_activity, self._record_activity),
            ("soul_driver", stable.notify_soul_driver, self._notify_soul_driver),
            (
                "consolidation",
                stable.log_memory and self.consolidation_service is not None,
                self._schedule_consolidation,
            ),
        )
        steps = dict(state.get("steps") or {})
        pending: list[str] = []
        for step, enabled, operation in operations:
            if steps.get(step):
                continue
            try:
                if enabled:
                    await operation(stable)
                state = await self._mark_step(stable.turn_id, step, state)
                steps = dict(state.get("steps") or {})
            except Exception as exc:
                logger.error("Post-turn step failed turn=%s step=%s: %s", stable.turn_id, step, exc)
                if self.journal is not None:
                    await self.journal.mark_failed(str(stable.turn_id), step, exc)
                pending = [
                    name
                    for name in POST_TURN_STEPS
                    if not steps.get(name)
                ]
                if stable.strict:
                    raise
                return CompanionInteractionResult(
                    turn_id=stable.turn_id,
                    pending_steps=tuple(pending),
                )

        if self.journal is not None:
            await self.journal.mark_completed(str(stable.turn_id))
        return CompanionInteractionResult(turn_id=stable.turn_id)

    async def recover_pending(self) -> list[CompanionInteractionResult]:
        if self.journal is None:
            return []
        results = []
        for record in await self.journal.pending():
            context_data = record["companion_context"]
            interaction = CompanionInteraction(
                companion_context=CompanionContext(**context_data),
                user_message=str(record.get("user_message") or ""),
                assistant_message=str(record.get("assistant_message") or ""),
                turn_id=str(record["turn_id"]),
                assistant_reasoning=str(record.get("assistant_reasoning") or ""),
                user_name=record.get("user_name"),
                companion_name=record.get("companion_name"),
                save_history=bool(record.get("save_history", True)),
                log_memory=bool(record.get("log_memory", True)),
                update_soul_activity=bool(record.get("update_soul_activity", True)),
                notify_soul_driver=bool(record.get("notify_soul_driver", True)),
            )
            results.append(await self.record(interaction))
        return results

    async def _begin(self, interaction: CompanionInteraction) -> dict[str, Any]:
        if self.journal is None:
            return {"status": "pending", "steps": {}}
        return await self.journal.begin({
            "turn_id": interaction.turn_id,
            "companion_context": {
                "session_id": interaction.companion_context.session_id,
                "user_id": interaction.companion_context.user_id,
                "character_id": interaction.companion_context.character_id,
                "user_name": interaction.companion_context.user_name,
            },
            "user_message": interaction.user_message,
            "assistant_message": interaction.assistant_message,
            "assistant_reasoning": interaction.assistant_reasoning,
            "user_name": interaction.user_name,
            "companion_name": interaction.companion_name,
            "save_history": interaction.save_history,
            "log_memory": interaction.log_memory,
            "update_soul_activity": interaction.update_soul_activity,
            "notify_soul_driver": interaction.notify_soul_driver,
        })

    async def _mark_step(
        self,
        turn_id: str | None,
        step: str,
        state: dict[str, Any],
    ) -> dict[str, Any]:
        if self.journal is not None:
            return await self.journal.mark_step(str(turn_id), step)
        return {**state, "steps": {**state.get("steps", {}), step: True}}

    async def record_activity(self, *, strict: bool = False) -> None:
        soul_service = self.soul_service

        try:
            soul_service.update_last_interaction()
        except Exception as exc:
            logger.error("Failed to record companion activity: %s", exc)
            if strict:
                raise

    async def _save_turn_history(self, interaction: CompanionInteraction) -> None:
        await self.session_manager.add_turn(
            interaction.companion_context,
            interaction.user_message,
            interaction.assistant_message,
            turn_id=interaction.turn_id,
            assistant_reasoning=interaction.assistant_reasoning,
        )

    async def _record_activity(self, interaction: CompanionInteraction) -> None:
        self.soul_service.update_last_interaction()

    async def _notify_soul_driver(self, interaction: CompanionInteraction) -> None:
        context = interaction.companion_context
        await self.soul_service.on_interaction(
            interaction.user_message,
            interaction.assistant_message,
            {
                "turn_id": interaction.turn_id,
                "session_id": context.session_id,
                "user_id": context.user_id,
                "character_id": context.character_id,
            },
        )

    async def _record_turn(self, interaction: CompanionInteraction) -> Optional[str]:
        memory_service = self.memory_service

        context = interaction.companion_context
        turn_id = await memory_service.record_turn(
            context,
            user_message=interaction.user_message,
            assistant_message=interaction.assistant_message,
            user_name=interaction.user_name,
            companion_name=interaction.companion_name,
            turn_id=interaction.turn_id,
        )
        logger.info("Conversation turn recorded turn=%s", turn_id)
        return str(turn_id)

    async def _schedule_consolidation(self, interaction: CompanionInteraction) -> None:
        await self.consolidation_service.schedule(interaction.companion_context)
