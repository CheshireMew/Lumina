import asyncio
import logging

from core.events.bus import get_event_bus
from core.protocol import EventPacket, EventType

logger = logging.getLogger("ChatTurnEventAdapter")


class ChatTurnEventAdapter:
    """Transport adapter from EventBus input events to CompanionRuntime."""

    def __init__(self, companion_runtime):
        self.bus = get_event_bus()
        self.companion_runtime = companion_runtime
        self.subscribed = False
        self.current_task = None
        self._dedupe_lock = asyncio.Lock()
        self._last_request_signature = ""
        self._last_request_time = 0.0

    def start(self):
        if self.subscribed:
            return

        self.bus.subscribe(EventType.INPUT_TEXT, self.handle_input_text)
        self.subscribed = True
        logger.info("Chat turn event adapter started")

    async def handle_input_text(self, event):
        if self.current_task and not self.current_task.done():
            logger.info("Interrupting active chat turn for new input")
            self.current_task.cancel()

        self.current_task = asyncio.create_task(self._process_input_text(event))

    async def _process_input_text(self, event):
        try:
            packet = self._coerce_packet(event.data)
            if packet is None:
                return

            if await self._is_duplicate(packet):
                return

            async for turn_event in self.companion_runtime.stream_text_packet(packet):
                await self._emit_turn_event(packet.session_id, turn_event)

        except asyncio.CancelledError:
            pass
        except Exception as exc:
            logger.error("Chat turn processing failed: %s", exc)
            session_id = self._event_session_id(event)
            await self.bus.emit(
                EventType.SYSTEM_STATUS,
                EventPacket(
                    session_id=session_id,
                    type=EventType.SYSTEM_STATUS,
                    source="core.chat_turn",
                    payload={"status": "error", "details": str(exc)},
                ),
            )

    def _coerce_packet(self, data):
        if isinstance(data, EventPacket):
            return data
        if isinstance(data, dict):
            return EventPacket(**data)
        return None

    async def _is_duplicate(self, packet: EventPacket) -> bool:
        text_content = str(packet.payload.get("text", ""))
        request_signature = f"{packet.session_id}:{text_content}"

        async with self._dedupe_lock:
            current_time = asyncio.get_event_loop().time()
            is_duplicate = (
                self._last_request_signature == request_signature
                and current_time - self._last_request_time < 2.0
            )
            self._last_request_signature = request_signature
            self._last_request_time = current_time

        if is_duplicate:
            logger.warning("Duplicate chat turn ignored: %s", request_signature)
        return is_duplicate

    async def _emit_turn_event(self, session_id: int, turn_event):
        event_type = {
            "started": EventType.BRAIN_THINKING,
            "delta": EventType.BRAIN_RESPONSE,
            "ended": EventType.BRAIN_RESPONSE_END,
        }.get(turn_event.kind)

        if not event_type:
            logger.warning("Unknown chat turn event kind: %s", turn_event.kind)
            return

        await self.bus.emit(
            event_type,
            EventPacket(
                session_id=session_id,
                type=event_type,
                source="core.chat_turn",
                payload=turn_event.payload,
            ),
        )

    def _event_session_id(self, event) -> int:
        data = getattr(event, "data", None)
        if isinstance(data, EventPacket):
            return data.session_id
        if isinstance(data, dict):
            return int(data.get("session_id") or 0)
        return 0
