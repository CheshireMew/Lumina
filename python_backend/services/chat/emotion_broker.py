import logging
import re
import time
from typing import Any

from core.protocol import EventPacket, EventType

logger = logging.getLogger("EmotionBroker")


class EmotionBroker:
    id = "system.emotion_broker"

    def __init__(self, event_bus, config: Any):
        self.event_bus = event_bus
        self.config = config
        settings = config.get_provider_settings(self.id)
        pattern = settings.get(
            "tag_pattern",
            r"[\[\(](joy|happy|sad|angry|surprised|neutral|thinking|embarrassed)[\]\)]",
        )
        try:
            self.tag_pattern = re.compile(pattern, re.IGNORECASE)
        except re.error:
            self.tag_pattern = re.compile(r"[\[\(](joy|sad|angry|neutral)[\]\)]", re.IGNORECASE)
        self.current_emotion = settings.get("default_emotion", "neutral")
        self.token_buffer = ""
        self.buffer_max_len = 50
        self._subscriptions: list[int] = []

    def start(self) -> None:
        if self._subscriptions:
            return
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.BRAIN_RESPONSE, self.handle_brain_response)
        )
        self._subscriptions.append(
            self.event_bus.subscribe(EventType.BRAIN_RESPONSE_END, self.handle_response_end)
        )
        logger.info("Emotion broker started")

    async def stop(self) -> None:
        for subscription_id in self._subscriptions:
            self.event_bus.unsubscribe(subscription_id)
        self._subscriptions.clear()
        self.token_buffer = ""

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

        matches = self.tag_pattern.findall(self.token_buffer)
        if not matches:
            return

        new_emotion = matches[-1].lower()
        if new_emotion == "happy":
            new_emotion = "joy"

        if new_emotion != self.current_emotion:
            self.current_emotion = new_emotion
            await self._broadcast_emotion(new_emotion, getattr(packet, "session_id", 0))
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
                "timestamp": time.time(),
            },
        )
        await self.event_bus.emit(packet.type, packet)
