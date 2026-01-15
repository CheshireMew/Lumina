import re
import logging
from typing import Optional

from plugins.base import BaseSystemPlugin
from core.protocol import EventPacket, EventType

logger = logging.getLogger("EmotionBroker")

class EmotionBrokerPlugin(BaseSystemPlugin):
    """
    Single Source of Truth for Emotion Parsing.
    
    Listens to BRAIN_RESPONSE stream, extracts emotion tags,
    and broadcasts 'emotion:changed' events to all subscribers:
    - TTS (adjust voice style)
    - Avatar Driver (VMC/OSC)
    - Frontend Gateway (WebSocket -> Live2D/VRM/Sprite)
    """

    @property
    def id(self) -> str:
        return "system.emotion_broker"

    @property
    def name(self) -> str:
        return "Emotion Broker"

    @property
    def description(self) -> str:
        return "Single Source of Truth for parsing emotion tags from LLM responses."

    def __init__(self):
        super().__init__()
        self.tag_pattern: Optional[re.Pattern] = None
        self.current_emotion: str = "neutral"
        self.token_buffer: str = ""  # Buffer to handle tags split across chunks
        self.buffer_max_len: int = 50  # Keep buffer small

    async def initialize(self, context):
        super().initialize(context)
        
        # Compile regex from config
        pattern_str = self.config.get("tag_pattern", r"[\[\(](joy|happy|sad|angry|surprised|neutral)[\]\)]")
        try:
            self.tag_pattern = re.compile(pattern_str, re.IGNORECASE)
        except re.error as e:
            logger.error(f"Invalid tag_pattern regex: {e}")
            self.tag_pattern = re.compile(r"[\[\(](joy|sad|angry|neutral)[\]\)]", re.IGNORECASE)
        
        self.current_emotion = self.config.get("default_emotion", "neutral")
        
        # Subscribe to LLM output stream
        if hasattr(self.context, 'bus'):
            self.context.bus.subscribe(EventType.BRAIN_RESPONSE, self.handle_brain_response)
            # Also listen for response end to flush buffer
            self.context.bus.subscribe("brain_response_end", self.handle_response_end)
        
        logger.info("馃幁 Emotion Broker Online - Single Source of Truth for Emotions")

    async def handle_brain_response(self, event: EventPacket):
        """
        Scans token stream for emotion tags.
        """
        content = event.payload.get("content", "")
        if not content:
            return

        # Append to buffer (for tags split across chunks)
        self.token_buffer += content
        
        # Keep buffer from growing too large
        if len(self.token_buffer) > self.buffer_max_len:
            self.token_buffer = self.token_buffer[-self.buffer_max_len:]

        # Scan for tags
        matches = self.tag_pattern.findall(self.token_buffer)
        if matches:
            # Take the last detected emotion
            new_emotion = matches[-1].lower()
            
            # Normalize aliases
            if new_emotion == "happy":
                new_emotion = "joy"
            
            # Only broadcast if changed
            if new_emotion != self.current_emotion:
                self.current_emotion = new_emotion
                await self._broadcast_emotion(new_emotion, event.session_id)
            
            # Clear buffer after successful match to avoid re-triggering
            self.token_buffer = ""

    async def handle_response_end(self, event: EventPacket):
        """
        Flush buffer on response end.
        """
        self.token_buffer = ""

    async def _broadcast_emotion(self, emotion: str, session_id: int = 0):
        """
        Emit emotion:changed event to all subscribers.
        """
        logger.info(f"鉁?Emotion Changed: {emotion}")
        
        await self.context.bus.emit(EventPacket(
            session_id=session_id,
            type="emotion:changed",
            source=self.id,
            payload={
                "emotion": emotion,
                "timestamp": __import__("time").time()
            }
        ))
