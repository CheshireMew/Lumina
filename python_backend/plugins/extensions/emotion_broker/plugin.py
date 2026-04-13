import logging
import re

from core.interfaces.plugin import Plugin as BasePlugin
from core.protocol import EventPacket, EventType

logger = logging.getLogger("EmotionBroker")


class Plugin(BasePlugin):
    def __init__(self):
        super().__init__()
        self.tag_pattern: re.Pattern | None = None
        self.current_emotion = "neutral"
        self.token_buffer = ""
        self.buffer_max_len = 50

    async def load(self, context):
        await super().load(context)
        pattern_str = self.config.get(
            "tag_pattern",
            r"[\[\(](joy|happy|sad|angry|surprised|neutral|thinking|embarrassed)[\]\)]",
        )
        try:
            self.tag_pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error:
            self.tag_pattern = re.compile(r"[\[\(](joy|sad|angry|neutral)[\]\)]", re.IGNORECASE)

    async def enable(self):
        await super().enable()
        self.current_emotion = self.config.get("default_emotion", "neutral")
        self.context.subscribe(EventType.BRAIN_RESPONSE, self.handle_brain_response)
        self.context.subscribe(EventType.BRAIN_RESPONSE_END, self.handle_response_end)

    async def handle_brain_response(self, event):
        packet = event.data
        if not packet or not hasattr(packet, "payload"):
            return

        content = packet.payload.get("content", "")
        if not content:
            return

        self.token_buffer += content
        if len(self.token_buffer) > self.buffer_max_len:
            self.token_buffer = self.token_buffer[-self.buffer_max_len :]

        matches = self.tag_pattern.findall(self.token_buffer) if self.tag_pattern else []
        if not matches:
            return

        new_emotion = matches[-1].lower()
        if new_emotion == "happy":
            new_emotion = "joy"

        if new_emotion != self.current_emotion:
            self.current_emotion = new_emotion
            session_id = getattr(packet, "session_id", 0)
            await self._broadcast_emotion(new_emotion, session_id)
        self.token_buffer = ""

    async def handle_response_end(self, _event):
        self.token_buffer = ""

    async def _broadcast_emotion(self, emotion: str, session_id: int = 0):
        packet = EventPacket(
            session_id=session_id,
            type=EventType.EMOTION_CHANGED,
            source=self.id,
            payload={
                "emotion": emotion,
                "timestamp": __import__("time").time(),
            },
        )
        await self.context.emit(packet.type, packet)

    def get_metadata(self) -> dict:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "Emotion Broker",
                "description": "Single source of truth for parsing and broadcasting emotions from chat output.",
                "func_tag": "Chat",
            }
        )
        return metadata
