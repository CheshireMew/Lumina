import sys
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.protocol import EventPacket, EventType
from services.chat.service import TextTurnRequest, TurnStreamEvent
from services.companion.context import CompanionContext
from services.companion.runtime import CompanionRuntime


def context() -> CompanionContext:
    return CompanionContext(
        session_id=7,
        user_id="u",
        character_id="hiyori",
        user_name="Ada",
    )


class FakeChatTurnService:
    def __init__(self):
        self.requests: list[TextTurnRequest] = []

    def build_text_turn_request(self, packet: EventPacket) -> TextTurnRequest:
        return TextTurnRequest(
            turn_id=str(packet.turn_id),
            client_id=packet.client_id,
            generation=packet.generation,
            text=packet.payload["text"],
            companion_context=context(),
            user_name="Ada",
            model=packet.payload.get("model"),
        )

    async def stream_text_turn(self, request: TextTurnRequest):
        self.requests.append(request)
        yield TurnStreamEvent(kind="started", payload={"mode": request.mode, "text": request.text})
        yield TurnStreamEvent(kind="delta", payload={"content": "hello"})
        yield TurnStreamEvent(kind="delta", payload={"content": " world"})
        yield TurnStreamEvent(kind="ended", payload={})


@pytest.mark.anyio
async def test_runtime_streams_text_packet_through_chat_turn_boundary():
    chat_service = FakeChatTurnService()
    runtime = CompanionRuntime(chat_turn_service=chat_service)
    packet = EventPacket(
        client_id="client-7",
        turn_id="turn-7",
        session_id=7,
        generation=2,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "ping", "model": "m"},
    )

    events = [event async for event in runtime.stream_text_packet(packet)]

    assert [event.kind for event in events] == ["started", "delta", "delta", "ended"]
    assert chat_service.requests == [
        TextTurnRequest(
            turn_id="turn-7",
            client_id="client-7",
            generation=2,
            text="ping",
            companion_context=context(),
            user_name="Ada",
            model="m",
        )
    ]


@pytest.mark.anyio
async def test_runtime_collects_text_turn_delta_content_only():
    runtime = CompanionRuntime(chat_turn_service=FakeChatTurnService())
    request = TextTurnRequest(
        turn_id="turn-7",
        client_id="client-7",
        generation=2,
        text="ping",
        companion_context=context(),
    )

    assert await runtime.collect_text_turn(request) == "hello world"


def test_runtime_requires_chat_turn_service():
    with pytest.raises(ValueError, match="ChatTurnService"):
        CompanionRuntime(chat_turn_service=None)
