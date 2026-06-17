import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, MagicMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.protocol import EventPacket, EventType
from services.chat.service import ChatTurnService, TextTurnRequest
from services.companion.context import CompanionContext, CompanionContextResolver
from services.companion.interaction import CompanionInteraction, CompanionInteractionRecorder


def companion_context(
    *,
    session_id: int = 1,
    user_id: str = "u",
    character_id: str = "c",
    user_name: str | None = None,
) -> CompanionContext:
    return CompanionContext(
        session_id=session_id,
        user_id=user_id,
        character_id=character_id,
        user_name=user_name,
    )


class FakePipeline:
    def __init__(self, tokens=None):
        self.tokens = tokens or ["Hello", " world"]
        self.calls = []

    async def run(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        for token in self.tokens:
            yield token


def fake_context_resolver(character_id: str = "lillian") -> CompanionContextResolver:
    return CompanionContextResolver(
        SimpleNamespace(get_active_character_id=lambda: character_id)
    )


def fake_recorder() -> SimpleNamespace:
    return SimpleNamespace(record=AsyncMock())


def fake_session_manager(history=None) -> SimpleNamespace:
    return SimpleNamespace(
        load_session=AsyncMock(
            return_value=SimpleNamespace(short_term_history=history or [])
        )
    )


@pytest.mark.anyio
async def test_build_text_turn_request_uses_packet_payload_and_active_character():
    service = ChatTurnService(
        pipeline=FakePipeline(),
        session_manager=fake_session_manager(),
        context_resolver=fake_context_resolver("lillian"),
        interaction_recorder=fake_recorder(),
    )

    packet = EventPacket(
        session_id=42,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hi", "user_id": "u1", "user_name": "Ada", "model": "m"},
    )

    request = service.build_text_turn_request(packet)

    assert request == TextTurnRequest(
        text="hi",
        companion_context=companion_context(
            session_id=42,
            user_id="u1",
            character_id="lillian",
            user_name="Ada",
        ),
        user_name="Ada",
        model="m",
    )


@pytest.mark.anyio
async def test_build_text_turn_request_uses_payload_character():
    service = ChatTurnService(
        pipeline=FakePipeline(),
        session_manager=fake_session_manager(),
        context_resolver=fake_context_resolver("lillian"),
        interaction_recorder=fake_recorder(),
    )

    packet = EventPacket(
        session_id=42,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hi", "character_id": "explicit-char"},
    )

    request = service.build_text_turn_request(packet)

    assert request.companion_context.character_id == "explicit-char"


@pytest.mark.anyio
async def test_stream_text_turn_emits_started_delta_and_ended_events():
    pipeline = FakePipeline(tokens=["A", "B"])
    session_manager = SimpleNamespace(
        load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
    )
    service = ChatTurnService(
        pipeline=pipeline,
        session_manager=session_manager,
        context_resolver=fake_context_resolver(),
        interaction_recorder=fake_recorder(),
    )

    events = [
        event
        async for event in service.stream_text_turn(
            TextTurnRequest(
                text=" hello ",
                companion_context=companion_context(session_id=1, user_id="u", character_id="c"),
            )
        )
    ]

    assert [event.kind for event in events] == ["started", "delta", "delta", "ended"]
    assert events[0].payload == {"mode": "chat", "text": "hello"}
    assert [event.payload.get("content") for event in events[1:3]] == ["A", "B"]
    assert pipeline.calls[0]["kwargs"]["enable_rag"] is False


@pytest.mark.anyio
async def test_stream_response_logs_turn_to_memory():
    pipeline = FakePipeline(tokens=["ok"])
    memory = SimpleNamespace(log_conversation=AsyncMock())
    session_manager = SimpleNamespace(add_turn=AsyncMock())
    soul = SimpleNamespace(
        update_last_interaction=MagicMock(),
        on_interaction=AsyncMock(),
    )
    service = ChatTurnService(
        pipeline=pipeline,
        session_manager=fake_session_manager(),
        context_resolver=fake_context_resolver(),
        interaction_recorder=CompanionInteractionRecorder(
            memory_service=memory,
            session_manager=session_manager,
            soul_service=soul,
        ),
    )

    response = [
        token
        async for token in service.stream_response(
            messages=[{"role": "user", "content": "ping"}],
            companion_context=companion_context(user_id="u", character_id="hiyori"),
            user_name="Ada",
        )
    ]

    assert response == ["ok"]
    session_manager.add_turn.assert_awaited_once()
    soul.update_last_interaction.assert_called_once_with()
    soul.on_interaction.assert_awaited_once()
    memory.log_conversation.assert_awaited_once_with(
        companion_context(user_id="u", character_id="hiyori"),
        "Ada: ping\nhiyori: ok",
    )


@pytest.mark.anyio
async def test_stream_response_records_companion_interaction():
    pipeline = FakePipeline(tokens=["ok"])
    recorder = SimpleNamespace(record=AsyncMock())
    service = ChatTurnService(
        pipeline=pipeline,
        session_manager=fake_session_manager(),
        context_resolver=fake_context_resolver(),
        interaction_recorder=recorder,
    )
    context = companion_context(session_id=7, user_id="u", character_id="hiyori")

    response = [
        token
        async for token in service.stream_response(
            messages=[{"role": "user", "content": "ping"}],
            companion_context=context,
            log_memory=False,
        )
    ]

    assert response == ["ok"]
    recorder.record.assert_awaited_once_with(
        CompanionInteraction(
            companion_context=context,
            user_message="ping",
            assistant_message="ok",
            save_history=True,
            log_memory=False,
        )
    )


def test_chat_turn_service_requires_core_dependencies():
    pipeline = FakePipeline()
    session_manager = fake_session_manager()
    context_resolver = fake_context_resolver()
    recorder = fake_recorder()

    with pytest.raises(ValueError, match="ChatPipeline"):
        ChatTurnService(
            pipeline=None,
            session_manager=session_manager,
            context_resolver=context_resolver,
            interaction_recorder=recorder,
        )

    with pytest.raises(ValueError, match="SessionManager"):
        ChatTurnService(
            pipeline=pipeline,
            session_manager=None,
            context_resolver=context_resolver,
            interaction_recorder=recorder,
        )

    with pytest.raises(ValueError, match="CompanionContextResolver"):
        ChatTurnService(
            pipeline=pipeline,
            session_manager=session_manager,
            context_resolver=None,
            interaction_recorder=recorder,
        )

    with pytest.raises(ValueError, match="CompanionInteractionRecorder"):
        ChatTurnService(
            pipeline=pipeline,
            session_manager=session_manager,
            context_resolver=context_resolver,
            interaction_recorder=None,
        )
