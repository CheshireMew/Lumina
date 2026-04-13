import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "python_backend"))
os.environ["LUMINA_ENV"] = "dev"

from core.events.bus import Event
from core.manifest import PluginManifest
from core.protocol import EventPacket, EventType
from plugins.extensions.emotion_broker.plugin import Plugin as EmotionBrokerPlugin
from services.chat_bridge import BasicChatBridge


class FakePluginContext:
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


class FailingChatService:
    async def build_turn_messages(self, user_id, character_id, text):
        return [{"role": "user", "content": text}]

    async def stream_response(self, **kwargs):
        raise RuntimeError("boom")
        yield ""


@pytest.mark.asyncio
async def test_emotion_broker_emits_packet_with_top_level_session_id():
    plugin = EmotionBrokerPlugin()
    plugin._bind_manifest(PluginManifest(id="system.emotion_broker"))

    context = FakePluginContext()
    await plugin.load(context)

    await plugin._broadcast_emotion("joy", session_id=7)

    event_type, packet = context.emitted[0]
    assert event_type == EventType.EMOTION_CHANGED
    assert packet.session_id == 7
    assert packet.payload == {"emotion": "joy", "timestamp": packet.payload["timestamp"]}


@pytest.mark.asyncio
async def test_chat_bridge_emits_schema_valid_system_status_on_failure():
    bridge = BasicChatBridge(FailingChatService())
    bridge.bus = FakeBus()

    packet = EventPacket(
        session_id=3,
        type=EventType.INPUT_TEXT,
        source="frontend",
        payload={"text": "hello"},
    )

    await bridge._process_chat(Event(type=EventType.INPUT_TEXT, data=packet, source="frontend"))

    status_events = [
        emitted
        for emitted in bridge.bus.emitted
        if emitted[0] == EventType.SYSTEM_STATUS
    ]

    assert len(status_events) == 1
    _, status_packet, _ = status_events[0]
    assert status_packet.session_id == 3
    assert status_packet.payload["status"] == "error"
    assert "boom" in status_packet.payload["details"]
