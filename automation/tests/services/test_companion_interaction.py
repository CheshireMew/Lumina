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
    memory = SimpleNamespace(log_conversation=AsyncMock(return_value="log-1"))
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
            user_name="Ada",
        )
    )

    session_manager.add_turn.assert_awaited_once_with(context, "ping", "ok")
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_awaited_once_with(
        "ping",
        "ok",
        {"session_id": 7, "user_id": "u", "character_id": "hiyori"},
    )
    memory.log_conversation.assert_awaited_once_with(context, "Ada: ping\nhiyori: ok")
    assert result == CompanionInteractionResult(memory_log_id="log-1")


@pytest.mark.anyio
async def test_respects_history_and_memory_flags():
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    memory = SimpleNamespace(log_conversation=AsyncMock())
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
    memory.log_conversation.assert_not_awaited()


@pytest.mark.anyio
async def test_manual_memory_recording_can_skip_soul_driver_notification():
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    memory = SimpleNamespace(log_conversation=AsyncMock(return_value="log-2"))
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
            user_name="Ada",
            companion_name="Lumina",
            save_history=False,
            notify_soul_driver=False,
            strict=True,
        )
    )

    assert result == CompanionInteractionResult(memory_log_id="log-2")
    session_manager.add_turn.assert_not_awaited()
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_not_awaited()
    memory.log_conversation.assert_awaited_once_with(
        context,
        "Ada: (Silence)\nLumina: noticed something",
    )


def test_recorder_requires_all_side_effect_dependencies():
    memory = SimpleNamespace(log_conversation=AsyncMock())
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
