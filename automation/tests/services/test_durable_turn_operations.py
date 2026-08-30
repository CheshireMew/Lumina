import json
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

from memory.consolidation import MemoryConsolidationService
from services.companion.context import CompanionContext
from services.companion.interaction import CompanionInteraction, CompanionInteractionRecorder
from services.companion.post_turn_journal import PostTurnJournal

pytestmark = pytest.mark.anyio


def companion_context() -> CompanionContext:
    return CompanionContext(
        session_id=7,
        user_id="ada",
        character_id="hiyori",
    )


async def test_post_turn_journal_resumes_at_failed_step_without_duplicate_history(tmp_path):
    journal = PostTurnJournal(tmp_path / "post-turn")
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    memory_service = SimpleNamespace(
        record_turn=AsyncMock(
            side_effect=[RuntimeError("memory temporarily unavailable"), "turn-1"]
        )
    )
    soul_service = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    recorder = CompanionInteractionRecorder(
        memory_service=memory_service,
        session_manager=session_manager,
        soul_service=soul_service,
        journal=journal,
    )
    interaction = CompanionInteraction(
        companion_context=companion_context(),
        user_message="ping",
        assistant_message="pong",
        turn_id="turn-1",
    )

    first = await recorder.record(interaction)

    assert first.turn_id == "turn-1"
    assert first.pending_steps[0] == "memory"
    session_manager.add_turn.assert_awaited_once()
    soul_service.update_last_interaction.assert_not_called()

    recovered = await recorder.recover_pending()

    assert [result.turn_id for result in recovered] == ["turn-1"]
    assert recovered[0].pending_steps == ()
    session_manager.add_turn.assert_awaited_once()
    assert memory_service.record_turn.await_count == 2
    soul_service.update_last_interaction.assert_called_once_with()
    soul_service.on_interaction.assert_awaited_once()
    assert await journal.pending() == []
    record = await journal.get("turn-1")
    assert record is not None
    assert record["status"] == "completed"
    assert all(record["steps"].values())


async def test_memory_consolidation_persists_job_before_committing_memories():
    turns = [
        {"id": "turn-1", "user_message": "I like tea", "assistant_message": "Noted"},
        {"id": "turn-2", "user_message": "Green tea", "assistant_message": "Okay"},
    ]
    driver = SimpleNamespace(
        query=AsyncMock(return_value=[]),
        create=AsyncMock(return_value="job"),
        update=AsyncMock(),
    )
    memory_service = SimpleNamespace(
        driver=driver,
        get_unprocessed_turns=AsyncMock(return_value=turns),
        create_memory_item=AsyncMock(return_value="memory-1"),
        mark_turns_processed=AsyncMock(),
    )
    llm_driver = SimpleNamespace(
        chat_completion=AsyncMock(
            return_value=json.dumps(
                {
                    "memories": [
                        {
                            "content": "Ada prefers green tea.",
                            "memory_type": "preference",
                            "confidence": 0.9,
                            "importance": 0.7,
                        }
                    ]
                }
            )
        )
    )
    llm_manager = SimpleNamespace(
        get_driver=AsyncMock(return_value=llm_driver),
        get_parameters=MagicMock(return_value={"temperature": 0.2}),
        get_model_name=MagicMock(return_value="memory-model"),
    )
    service = MemoryConsolidationService(
        memory_service=memory_service,
        llm_manager=llm_manager,
        threshold=2,
    )

    prepared = await service._prepare_available(companion_context())

    assert prepared is not None
    driver.create.assert_awaited_once()
    created_job = driver.create.await_args.args[1]
    assert created_job["status"] == "pending"
    assert created_job["turn_ids"] == ["turn-1", "turn-2"]
    memory_service.create_memory_item.assert_not_awaited()

    await service._run_job(companion_context(), prepared)

    memory_service.create_memory_item.assert_awaited_once()
    memory_kwargs = memory_service.create_memory_item.await_args.kwargs
    assert memory_kwargs["source_turn_ids"] == ["turn-1", "turn-2"]
    assert memory_kwargs["metadata"]["consolidation_job_id"] == created_job["id"]
    memory_service.mark_turns_processed.assert_awaited_once_with(["turn-1", "turn-2"])
    completed_update = driver.update.await_args_list[-1]
    assert completed_update.args[0] == "memory_consolidation_jobs"
    assert completed_update.args[1] == created_job["id"]
    assert completed_update.args[2]["status"] == "completed"


async def test_memory_consolidation_rejects_missing_durable_job():
    driver = SimpleNamespace(update=AsyncMock(return_value=False))
    service = MemoryConsolidationService(
        memory_service=SimpleNamespace(driver=driver),
        llm_manager=SimpleNamespace(),
        threshold=2,
    )

    with pytest.raises(RuntimeError, match="does not exist"):
        await service._update_job(
            "memory_consolidation_jobs",
            "missing-job",
            {"status": "running"},
        )
