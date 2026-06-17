import logging
from typing import Any, AsyncGenerator

from core.protocol import EventPacket
from services.chat.service import TextTurnRequest, TurnStreamEvent

logger = logging.getLogger("CompanionRuntime")


class CompanionRuntime:
    """Single backend boundary for companion-facing interactions."""

    def __init__(self, *, chat_turn_service: Any):
        if chat_turn_service is None:
            raise ValueError("CompanionRuntime requires ChatTurnService")

        self.chat_turn_service = chat_turn_service

    def build_text_turn_request(self, packet: EventPacket) -> TextTurnRequest:
        return self.chat_turn_service.build_text_turn_request(packet)

    async def stream_text_packet(
        self,
        packet: EventPacket,
    ) -> AsyncGenerator[TurnStreamEvent, None]:
        request = self.build_text_turn_request(packet)
        async for event in self.stream_text_turn(request):
            yield event

    async def stream_text_turn(
        self,
        request: TextTurnRequest,
    ) -> AsyncGenerator[TurnStreamEvent, None]:
        async for event in self.chat_turn_service.stream_text_turn(request):
            yield event

    async def collect_text_turn(self, request: TextTurnRequest) -> str:
        content = ""
        async for event in self.stream_text_turn(request):
            if event.kind == "delta":
                content += str(event.payload.get("content") or "")
        return content
