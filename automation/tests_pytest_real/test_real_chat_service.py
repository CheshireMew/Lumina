import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.chat.service import ChatTurnService, TextTurnRequest
from services.companion.context import CompanionContext, CompanionContextResolver


def companion_context(
    *,
    session_id: int = 1,
    user_id: str = "user",
    character_id: str = "hiyori",
) -> CompanionContext:
    return CompanionContext(
        session_id=session_id,
        user_id=user_id,
        character_id=character_id,
    )


class StreamingPipeline:
    def __init__(self):
        self.calls = []

    async def run(self, messages, **kwargs):
        self.calls.append((messages, kwargs))
        yield "first"
        yield " second"


def chat_service(pipeline, session_manager=None) -> ChatTurnService:
    session_manager = session_manager or SimpleNamespace(
        load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
    )
    return ChatTurnService(
        pipeline=pipeline,
        session_manager=session_manager,
        context_resolver=CompanionContextResolver(
            SimpleNamespace(get_active_character_id=lambda: "hiyori")
        ),
        interaction_recorder=SimpleNamespace(record=AsyncMock()),
    )


@pytest.mark.anyio
async def test_chat_turn_service_collects_pipeline_response():
    pipeline = StreamingPipeline()
    service = chat_service(pipeline)

    content = await service.collect_response(
        messages=[{"role": "user", "content": "hello"}],
        companion_context=companion_context(user_id="user", character_id="hiyori"),
        log_memory=False,
    )

    assert content == "first second"
    assert pipeline.calls[0][1]["companion_context"].user_id == "user"


@pytest.mark.anyio
async def test_chat_turn_service_includes_short_term_history():
    pipeline = StreamingPipeline()
    session_manager = SimpleNamespace(
        load_session=AsyncMock(
            return_value=SimpleNamespace(
                short_term_history=[
                    {"role": "user", "content": "old"},
                    {"role": "assistant", "content": "reply"},
                ]
            )
        )
    )
    service = chat_service(pipeline, session_manager=session_manager)

    messages = await service.build_turn_messages(
        companion_context(user_id="u", character_id="c"),
        "new",
        history_limit=5,
    )

    assert messages == [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "reply"},
        {"role": "user", "content": "new"},
    ]


@pytest.mark.anyio
async def test_chat_turn_service_skips_empty_text_turns():
    service = chat_service(StreamingPipeline())

    events = [
        event
        async for event in service.stream_text_turn(
            TextTurnRequest(text="   ", companion_context=companion_context(session_id=1))
        )
    ]

    assert events == []
