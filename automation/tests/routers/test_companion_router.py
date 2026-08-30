import sys
from pathlib import Path
from types import SimpleNamespace

import pytest
from fastapi import HTTPException

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from routers.companion import CompanionMessageRequest, send_companion_message
from services.chat.service import TurnStreamEvent


class FakeCompanionRuntime:
    def __init__(self):
        self.packet = None
        self.request = SimpleNamespace()

    def build_text_turn_request(self, packet):
        self.packet = packet
        return self.request

    async def stream_text_packet(self, packet):
        self.build_text_turn_request(packet)
        yield TurnStreamEvent(kind="started", payload={"mode": "chat", "text": "hello"})
        yield TurnStreamEvent(kind="delta", payload={"content": "hello"})
        yield TurnStreamEvent(kind="ended", payload={})


@pytest.mark.anyio
async def test_send_companion_message_uses_companion_runtime_boundary():
    runtime = FakeCompanionRuntime()

    response = await send_companion_message(
        CompanionMessageRequest(
            text=" hello ",
            session_id=9,
            generation=4,
            client_id="rest-client",
            turn_id="turn-9",
            user_id="u",
            character_id="hiyori",
            user_name="Ada",
            model="m",
        ),
        companion_runtime=runtime,
    )

    assert response == {
        "turn_id": "turn-9",
        "session_id": 9,
        "generation": 4,
        "status": "completed",
        "content": "hello",
        "reasoning": "",
    }
    assert runtime.packet.client_id == "rest-client"
    assert runtime.packet.turn_id == "turn-9"
    assert runtime.packet.session_id == 9
    assert runtime.packet.payload == {
        "text": "hello",
        "user_id": "u",
        "character_id": "hiyori",
        "user_name": "Ada",
        "model": "m",
    }


@pytest.mark.anyio
async def test_send_companion_message_rejects_blank_text():
    with pytest.raises(HTTPException) as exc_info:
        await send_companion_message(
            CompanionMessageRequest(text=" "),
            companion_runtime=FakeCompanionRuntime(),
        )

    assert exc_info.value.status_code == 400
