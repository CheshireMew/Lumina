import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.companion.context import CompanionContext
from services.companion.interaction import (
    CompanionInteraction,
    CompanionInteractionRecorder,
    CompanionInteractionResult,
)


def companion_context() -> CompanionContext:
    return CompanionContext(
        session_id=7,
        user_id="u",
        character_id="hiyori",
        user_name="Ada",
    )


@pytest.mark.anyio
async def test_records_complete_companion_interaction():
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    memory = SimpleNamespace(record_turn=AsyncMock(return_value="turn-1"))
    recorder = CompanionInteractionRecorder(
        session_manager=session_manager,
        soul_service=soul,
        memory_service=memory,
    )

    context = companion_context()
    result = await recorder.record(
        CompanionInteraction(
            companion_context=context,
            user_message="ping",
            assistant_message="ok",
            turn_id="turn-1",
            user_name="Ada",
        )
    )

    session_manager.add_turn.assert_awaited_once_with(
        context,
        "ping",
        "ok",
        turn_id="turn-1",
        assistant_reasoning="",
    )
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_awaited_once_with(
        "ping",
        "ok",
        {
            "turn_id": "turn-1",
            "session_id": 7,
            "user_id": "u",
            "character_id": "hiyori",
        },
    )
    memory.record_turn.assert_awaited_once_with(
        context,
        user_message="ping",
        assistant_message="ok",
        user_name="Ada",
        companion_name=None,
        turn_id="turn-1",
    )
    assert result == CompanionInteractionResult(turn_id="turn-1")


@pytest.mark.anyio
async def test_respects_history_and_memory_flags():
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    memory = SimpleNamespace(record_turn=AsyncMock())
    recorder = CompanionInteractionRecorder(
        session_manager=session_manager,
        soul_service=soul,
        memory_service=memory,
    )

    await recorder.record(
        CompanionInteraction(
            companion_context=companion_context(),
            user_message="ping",
            assistant_message="ok",
            save_history=False,
            log_memory=False,
        )
    )

    session_manager.add_turn.assert_not_awaited()
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_awaited_once()
    memory.record_turn.assert_not_awaited()


@pytest.mark.anyio
async def test_manual_memory_recording_can_skip_soul_driver_notification():
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    memory = SimpleNamespace(record_turn=AsyncMock(return_value="turn-2"))
    recorder = CompanionInteractionRecorder(
        session_manager=session_manager,
        soul_service=soul,
        memory_service=memory,
    )

    context = companion_context()
    result = await recorder.record(
        CompanionInteraction(
            companion_context=context,
            user_message="",
            assistant_message="noticed something",
            turn_id="turn-2",
            user_name="Ada",
            companion_name="Lumina",
            save_history=False,
            notify_soul_driver=False,
            strict=True,
        )
    )

    assert result == CompanionInteractionResult(turn_id="turn-2")
    session_manager.add_turn.assert_not_awaited()
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_not_awaited()
    memory.record_turn.assert_awaited_once_with(
        context,
        user_message="",
        assistant_message="noticed something",
        user_name="Ada",
        companion_name="Lumina",
        turn_id="turn-2",
    )


def test_recorder_requires_all_side_effect_dependencies():
    memory = SimpleNamespace(record_turn=AsyncMock())
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )

    with pytest.raises(ValueError, match="MemoryService"):
        CompanionInteractionRecorder(
            memory_service=None,
            session_manager=session_manager,
            soul_service=soul,
        )

    with pytest.raises(ValueError, match="SessionManager"):
        CompanionInteractionRecorder(
            memory_service=memory,
            session_manager=None,
            soul_service=soul,
        )

    with pytest.raises(ValueError, match="SoulService"):
        CompanionInteractionRecorder(
            memory_service=memory,
            session_manager=session_manager,
            soul_service=None,
        )
