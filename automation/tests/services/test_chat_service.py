import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.protocol import EventPacket, EventType
from services.chat.service import ChatTurnService, TextTurnRequest


class FakePipeline:
    def __init__(self, tokens=None):
        self.tokens = tokens or ["Hello", " world"]
        self.calls = []

    async def run(self, messages, **kwargs):
        self.calls.append({"messages": messages, "kwargs": kwargs})
        for token in self.tokens:
            yield token


@pytest.mark.anyio
async def test_build_text_turn_request_uses_packet_payload_and_active_character():
    soul = SimpleNamespace(get_active_character_id=lambda: "lillian")
    service = ChatTurnService(pipeline=FakePipeline(), soul_service=soul)

    packet = EventPacket(
        session_id=42,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hi", "user_id": "u1", "user_name": "Ada", "model": "m"},
    )

    request = service.build_text_turn_request(packet)

    assert request == TextTurnRequest(
        session_id=42,
        text="hi",
        user_id="u1",
        character_id="lillian",
        user_name="Ada",
        model="m",
    )


@pytest.mark.anyio
async def test_build_text_turn_request_requires_soul_service_without_payload_character():
    service = ChatTurnService(pipeline=FakePipeline())

    packet = EventPacket(
        session_id=42,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hi"},
    )

    with pytest.raises(RuntimeError, match="SoulService is required"):
        service.build_text_turn_request(packet)


@pytest.mark.anyio
async def test_build_text_turn_request_uses_payload_character_without_soul_service():
    service = ChatTurnService(pipeline=FakePipeline())

    packet = EventPacket(
        session_id=42,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hi", "character_id": "explicit-char"},
    )

    request = service.build_text_turn_request(packet)

    assert request.character_id == "explicit-char"


@pytest.mark.anyio
async def test_stream_text_turn_emits_started_delta_and_ended_events():
    pipeline = FakePipeline(tokens=["A", "B"])
    session_manager = SimpleNamespace(
        load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
    )
    service = ChatTurnService(pipeline=pipeline, session_manager=session_manager)

    events = [
        event
        async for event in service.stream_text_turn(
            TextTurnRequest(session_id=1, text=" hello ", user_id="u", character_id="c")
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
    service = ChatTurnService(pipeline=pipeline, memory_service=memory)

    response = [
        token
        async for token in service.stream_response(
            messages=[{"role": "user", "content": "ping"}],
            user_id="u",
            user_name="Ada",
            character_id="hiyori",
        )
    ]

    assert response == ["ok"]
    memory.log_conversation.assert_awaited_once_with("hiyori", "Ada: ping\nhiyori: ok")
