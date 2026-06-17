import os
import sys
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "python_backend"))
os.environ["LUMINA_ENV"] = "dev"

from core.events.bus import Event
from core.manifest import CapabilityManifest
from core.protocol import EventPacket, EventType, InputTextPayload
from capability_modules.emotion_broker.module import Capability as EmotionBrokerModule
from services.chat.event_adapter import ChatTurnEventAdapter
from services.chat.service import ChatTurnService
from services.companion.context import CompanionContextResolver
from services.companion.runtime import CompanionRuntime


class FakeModuleContext:
    def __init__(self):
        self.emitted: list[tuple[str, EventPacket]] = []

    def get_config(self):
        return {}

    async def emit(self, event_type, packet):
        self.emitted.append((event_type, packet))


class FakeBus:
    def __init__(self):
        self.emitted: list[tuple[str, EventPacket, str]] = []

    async def emit(self, event_type, packet, source="system"):
        self.emitted.append((event_type, packet, source))


class FailingPipeline:
    async def run(self, *args, **kwargs):
        raise RuntimeError("boom")
        yield ""


class FakeSoulService:
    def get_active_character_id(self) -> str:
        return "hiyori"


@pytest.mark.anyio
async def test_emotion_broker_emits_packet_with_top_level_session_id():
    module = EmotionBrokerModule()
    module._bind_manifest(CapabilityManifest(id="system.emotion_broker"))

    context = FakeModuleContext()
    await module.load(context)

    await module._broadcast_emotion("joy", session_id=7)

    event_type, packet = context.emitted[0]
    assert event_type == EventType.EMOTION_CHANGED
    assert packet.session_id == 7
    assert packet.payload == {"emotion": "joy", "timestamp": packet.payload["timestamp"]}


@pytest.mark.anyio
async def test_chat_turn_event_adapter_emits_schema_valid_system_status_on_failure():
    chat_service = ChatTurnService(
        pipeline=FailingPipeline(),
        session_manager=SimpleNamespace(
            load_session=AsyncMock(return_value=SimpleNamespace(short_term_history=[]))
        ),
        context_resolver=CompanionContextResolver(FakeSoulService()),
        interaction_recorder=SimpleNamespace(record=AsyncMock()),
    )
    adapter = ChatTurnEventAdapter(CompanionRuntime(chat_turn_service=chat_service))
    adapter.bus = FakeBus()

    packet = EventPacket(
        session_id=3,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hello", "character_id": "hiyori"},
    )

    await adapter._process_input_text(Event(type=EventType.INPUT_TEXT, data=packet, source="frontend"))

    status_events = [
        emitted
        for emitted in adapter.bus.emitted
        if emitted[0] == EventType.SYSTEM_STATUS
    ]

    assert len(status_events) == 1
    _, status_packet, _ = status_events[0]
    assert status_packet.session_id == 3
    assert status_packet.payload["status"] == "error"
    assert "boom" in status_packet.payload["details"]


def test_input_text_payload_does_not_default_identity():
    payload = InputTextPayload(text="hello")

    assert payload.user_id is None
    assert payload.character_id is None
