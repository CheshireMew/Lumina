import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.chat.service import ChatTurnService, TextTurnRequest
from services.companion.context import CompanionContext, CompanionContextResolver
from services.companion.context_pack import CompanionContextPack


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

    async def run(self, **kwargs):
        self.calls.append(kwargs)
        yield "first"
        yield " second"


def chat_service(pipeline, session_manager=None) -> ChatTurnService:
    session_manager = session_manager or SimpleNamespace(
        load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
    )
    async def build_context_pack(*, companion_context, user_message, history_limit, enable_memory=True):
        state = await session_manager.load_session(companion_context)
        history = getattr(state, "short_term_history", []) or []
        return CompanionContextPack(
            identity=companion_context,
            user_message=user_message,
            recent_session_history=history[-history_limit:],
            system_prompt="System",
        )

    return ChatTurnService(
        pipeline=pipeline,
        session_manager=session_manager,
        context_resolver=CompanionContextResolver(
            SimpleNamespace(get_active_character_id=lambda: "hiyori")
        ),
        context_pack_builder=SimpleNamespace(build=AsyncMock(side_effect=build_context_pack)),
        interaction_recorder=SimpleNamespace(record=AsyncMock()),
    )


@pytest.mark.anyio
async def test_chat_turn_service_collects_pipeline_response():
    pipeline = StreamingPipeline()
    service = chat_service(pipeline)

    content = await service.collect_response(
        companion_context=companion_context(user_id="user", character_id="hiyori"),
        context_pack=CompanionContextPack(
            identity=companion_context(user_id="user", character_id="hiyori"),
            user_message="hello",
            system_prompt="System",
        ),
        log_memory=False,
    )

    assert content == "first second"
    assert pipeline.calls[0]["context_pack"].identity.user_id == "user"


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

    events = [
        event
        async for event in service.stream_text_turn(
            TextTurnRequest(
                text="new",
                companion_context=companion_context(user_id="u", character_id="c"),
                history_limit=5,
            )
        )
    ]

    pack = pipeline.calls[0]["context_pack"]
    assert [event.kind for event in events] == ["started", "delta", "delta", "ended"]
    assert pack.recent_session_history == [
        {"role": "user", "content": "old"},
        {"role": "assistant", "content": "reply"},
    ]
    assert pack.user_message == "new"


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
