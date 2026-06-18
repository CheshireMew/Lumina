import logging
from typing import Any, AsyncGenerator

from core.protocol import EventPacket, EventType
from services.chat.service import TextTurnRequest, TurnStreamEvent

logger = logging.getLogger("CompanionRuntime")


class CompanionRuntime:
    """Single backend boundary for companion-facing interactions."""

    def __init__(
        self,
        *,
        chat_turn_service: Any,
        context_resolver: Any = None,
        session_manager: Any = None,
    ):
        if chat_turn_service is None:
            raise ValueError("CompanionRuntime requires ChatTurnService")

        self.chat_turn_service = chat_turn_service
        self.context_resolver = context_resolver
        self.session_manager = session_manager
        self._interrupted = False

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
        self._interrupted = False
        async for event in self.chat_turn_service.stream_text_turn(request):
            if self._interrupted:
                yield TurnStreamEvent(kind="interrupted", payload={})
                return
            yield event

    async def collect_text_turn(self, request: TextTurnRequest) -> str:
        content = ""
        async for event in self.stream_text_turn(request):
            if event.kind == "delta":
                content += str(event.payload.get("content") or "")
        return content

    async def interrupt(self) -> None:
        self._interrupted = True

    async def reset_session(self, packet: EventPacket) -> int:
        if self.context_resolver is None:
            raise ValueError("CompanionRuntime requires CompanionContextResolver")
        if self.session_manager is None:
            raise ValueError("CompanionRuntime requires SessionManager")

        context = self.context_resolver.from_packet(packet)
        await self.session_manager.clear_history(context)
        return context.session_id

    async def handle_control_packet(self, packet: EventPacket) -> dict[str, Any]:
        action = str((packet.payload or {}).get("action") or "").strip()
        if packet.type == EventType.CONTROL_INTERRUPT or action == "interrupt":
            await self.interrupt()
            return {"action": "interrupt", "session_id": packet.session_id}
        if packet.type == EventType.CONTROL_SESSION or action == "reset":
            session_id = await self.reset_session(packet)
            return {"action": "reset", "session_id": session_id}
        return {"action": action or "noop", "session_id": packet.session_id}
