import asyncio
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
        self._turns: dict[tuple[str, int, str], asyncio.Event] = {}
        self._turns_lock = asyncio.Lock()

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
        turn_key = self._turn_key(request)
        cancel_event = asyncio.Event()
        async with self._turns_lock:
            if turn_key in self._turns:
                raise RuntimeError(f"Turn is already active: {request.turn_id}")
            self._turns[turn_key] = cancel_event

        try:
            async for event in self.chat_turn_service.stream_text_turn(request):
                if cancel_event.is_set():
                    yield TurnStreamEvent(
                        kind="ended",
                        payload={"status": "interrupted"},
                    )
                    return
                yield event
        finally:
            async with self._turns_lock:
                current = self._turns.get(turn_key)
                if current is cancel_event:
                    self._turns.pop(turn_key, None)

    async def collect_text_turn(self, request: TextTurnRequest) -> str:
        content = ""
        async for event in self.stream_text_turn(request):
            if event.kind == "delta":
                content += str(event.payload.get("content") or "")
        return content

    async def interrupt(
        self,
        *,
        client_id: str,
        session_id: int,
        turn_id: str | None = None,
    ) -> list[str]:
        interrupted: list[str] = []
        async with self._turns_lock:
            for (active_client_id, active_session_id, active_turn_id), event in self._turns.items():
                if active_client_id != client_id or active_session_id != session_id:
                    continue
                if turn_id and active_turn_id != turn_id:
                    continue
                event.set()
                interrupted.append(active_turn_id)
        return interrupted

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
            interrupted = await self.interrupt(
                client_id=packet.client_id,
                session_id=packet.session_id,
                turn_id=packet.turn_id or (packet.payload or {}).get("turn_id"),
            )
            return {
                "action": "interrupt",
                "session_id": packet.session_id,
                "turn_ids": interrupted,
            }
        if packet.type == EventType.CONTROL_SESSION or action == "reset":
            session_id = await self.reset_session(packet)
            return {"action": "reset", "session_id": session_id}
        return {"action": action or "noop", "session_id": packet.session_id}

    @staticmethod
    def _turn_key(request: TextTurnRequest) -> tuple[str, int, str]:
        return (
            request.client_id,
            request.companion_context.session_id,
            request.turn_id,
        )
