from __future__ import annotations

import asyncio
import json
import logging
import re
import uuid
from dataclasses import dataclass
from typing import Any, Literal

from pydantic import BaseModel, Field

from services.companion.context import CompanionContext

logger = logging.getLogger("memory.consolidation")


class ConsolidatedMemory(BaseModel):
    content: str = Field(min_length=3, max_length=1000)
    summary: str | None = Field(default=None, max_length=240)
    memory_type: Literal["episode", "preference", "fact", "relationship"] = "episode"
    confidence: float = Field(default=0.8, ge=0.0, le=1.0)
    importance: float = Field(default=0.5, ge=0.0, le=1.0)


class ConsolidationOutput(BaseModel):
    memories: list[ConsolidatedMemory] = Field(default_factory=list, max_length=10)


@dataclass(frozen=True)
class PreparedConsolidation:
    job_id: str
    turns: list[dict[str, Any]]
    turn_ids: list[str]


class MemoryConsolidationService:
    """Turn raw conversation records into validated, traceable long-term memories."""

    def __init__(self, *, memory_service: Any, llm_manager: Any, threshold: int = 20):
        self.memory_service = memory_service
        self.llm_manager = llm_manager
        self.threshold = max(2, threshold)
        self._tasks: dict[str, asyncio.Task[None]] = {}
        self._requested: set[str] = set()
        self._lock = asyncio.Lock()

    async def schedule(self, context: CompanionContext) -> None:
        key = context.character_id
        async with self._lock:
            current = self._tasks.get(key)
            if current is not None and not current.done():
                self._requested.add(key)
                return
            prepared = await self._prepare_available(context)
            if prepared is None:
                return
            task = asyncio.create_task(
                self._run_worker(context, prepared),
                name=f"memory-consolidation:{key}",
            )
            self._tasks[key] = task
            task.add_done_callback(
                lambda completed, task_key=key: self._task_finished(task_key, completed)
            )

    def _task_finished(self, key: str, task: asyncio.Task[None]) -> None:
        if self._tasks.get(key) is task:
            self._tasks.pop(key, None)
        if task.cancelled():
            return
        error = task.exception()
        if error is not None:
            logger.error("Memory consolidation task failed for %s: %s", key, error)

    async def _consolidate_available(self, context: CompanionContext) -> None:
        prepared = await self._prepare_available(context)
        if prepared is not None:
            await self._run_prepared_and_drain(context, prepared)

    async def _run_worker(
        self,
        context: CompanionContext,
        prepared: PreparedConsolidation,
    ) -> None:
        key = context.character_id
        current: PreparedConsolidation | None = prepared
        while True:
            if current is not None:
                await self._run_job(context, current)
            current = await self._prepare_available(context)
            if current is not None:
                continue

            async with self._lock:
                if key in self._requested:
                    self._requested.discard(key)
                    continue
                task = asyncio.current_task()
                if task is not None and self._tasks.get(key) is task:
                    self._tasks.pop(key, None)
                return

    async def _run_prepared_and_drain(
        self,
        context: CompanionContext,
        prepared: PreparedConsolidation,
    ) -> None:
        current: PreparedConsolidation | None = prepared
        while current is not None:
            await self._run_job(context, current)
            current = await self._prepare_available(context)

    async def _prepare_available(
        self,
        context: CompanionContext,
    ) -> PreparedConsolidation | None:
        while True:
            turns = await self.memory_service.get_unprocessed_turns(
                context,
                limit=self.threshold,
            )
            if len(turns) < self.threshold:
                return None

            turn_ids = [str(turn["id"]) for turn in turns if turn.get("id")]
            if len(turn_ids) != len(turns):
                raise ValueError("Conversation turn without id cannot be consolidated")

            job_id = str(
                uuid.uuid5(
                    uuid.NAMESPACE_URL,
                    f"lumina:memory:{context.character_id}:{':'.join(turn_ids)}",
                )
            )
            existing = await self.memory_service.driver.query(
                "SELECT * FROM memory_consolidation_jobs WHERE id = $job_id LIMIT 1;",
                {"job_id": job_id},
            )
            if existing and existing[0].get("status") == "completed":
                await self.memory_service.mark_turns_processed(turn_ids)
                continue

            job_payload = {
                "status": "pending",
                "turn_ids": turn_ids,
                "error": None,
                "metadata": {"user_id": context.user_id},
            }
            if existing:
                await self._update_job(
                    "memory_consolidation_jobs",
                    job_id,
                    job_payload,
                )
            else:
                await self.memory_service.driver.create(
                    "memory_consolidation_jobs",
                    {"id": job_id, "character_id": context.character_id, **job_payload},
                )
            return PreparedConsolidation(
                job_id=job_id,
                turns=turns,
                turn_ids=turn_ids,
            )

    async def _run_job(
        self,
        context: CompanionContext,
        prepared: PreparedConsolidation,
    ) -> None:
        job_id = prepared.job_id
        turns = prepared.turns
        turn_ids = prepared.turn_ids
        await self._update_job(
            "memory_consolidation_jobs",
            job_id,
            {"status": "running", "error": None},
        )

        try:
            output = await self._extract_memories(turns)
            for index, candidate in enumerate(output.memories):
                memory_id = str(uuid.uuid5(uuid.UUID(job_id), str(index)))
                await self.memory_service.create_memory_item(
                    context,
                    memory_id=memory_id,
                    content=candidate.content,
                    summary=candidate.summary,
                    memory_type=candidate.memory_type,
                    source_turn_ids=turn_ids,
                    confidence=candidate.confidence,
                    importance=candidate.importance,
                    metadata={"consolidation_job_id": job_id},
                )

            await self.memory_service.mark_turns_processed(turn_ids)
            await self._update_job(
                "memory_consolidation_jobs",
                job_id,
                {
                    "status": "completed",
                    "error": None,
                    "metadata": {
                        "user_id": context.user_id,
                        "memory_count": len(output.memories),
                    },
                },
            )
        except Exception as exc:
            try:
                await self._update_job(
                    "memory_consolidation_jobs",
                    job_id,
                    {"status": "failed", "error": str(exc)},
                )
            except Exception as status_exc:
                logger.error(
                    "Failed to persist consolidation failure job=%s: %s",
                    job_id,
                    status_exc,
                )
            raise

    async def _update_job(
        self,
        table: str,
        job_id: str,
        payload: dict[str, Any],
    ) -> None:
        updated = await self.memory_service.driver.update(table, job_id, payload)
        if updated is False:
            raise RuntimeError(f"Memory consolidation job does not exist: {job_id}")

    async def _extract_memories(self, turns: list[dict[str, Any]]) -> ConsolidationOutput:
        transcript = [
            {
                "turn_id": str(turn.get("id") or ""),
                "user": str(turn.get("user_message") or ""),
                "assistant": str(turn.get("assistant_message") or ""),
            }
            for turn in turns
        ]
        messages = [
            {
                "role": "system",
                "content": (
                    "Extract only durable user facts, preferences, meaningful events, and "
                    "relationship context useful in future conversations. Do not copy assistant "
                    "instructions or guesses. Return JSON only with this shape: "
                    '{"memories":[{"content":"...","summary":"...",'
                    '"memory_type":"episode|preference|fact|relationship",'
                    '"confidence":0.0,"importance":0.0}]}.'
                ),
            },
            {
                "role": "user",
                "content": json.dumps(transcript, ensure_ascii=False),
            },
        ]
        driver = await self.llm_manager.get_driver("memory")
        parameters = dict(self.llm_manager.get_parameters("memory"))
        temperature = float(parameters.pop("temperature", 0.2))
        result = await driver.chat_completion(
            messages,
            model=self.llm_manager.get_model_name("memory"),
            temperature=temperature,
            stream=False,
            **parameters,
        )
        return ConsolidationOutput.model_validate(self._parse_json(result))

    @staticmethod
    def _parse_json(value: Any) -> dict[str, Any]:
        text = str(value or "").strip()
        fenced = re.fullmatch(r"```(?:json)?\s*(.*?)\s*```", text, flags=re.DOTALL)
        if fenced:
            text = fenced.group(1)
        payload = json.loads(text)
        if not isinstance(payload, dict):
            raise ValueError("Memory consolidation output must be a JSON object")
        return payload

    async def close(self) -> None:
        tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)
        self._tasks.clear()
        self._requested.clear()
