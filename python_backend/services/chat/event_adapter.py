import asyncio
import logging

from core.protocol import EventPacket, EventType
from services.chat.service import TurnStreamEvent

logger = logging.getLogger("ChatTurnEventAdapter")


def classify_chat_error(exc: Exception) -> tuple[str, str]:
    """Return a stable user-facing code and message without leaking provider internals."""
    detail = str(exc).lower()
    if "402" in detail or "payment required" in detail or "insufficient balance" in detail:
        return "provider_payment_required", "Pollinations 账户额度不足，请检查账户或更换模型服务。"
    if "401" in detail or "403" in detail or "authentication" in detail or "api key" in detail:
        return "provider_authentication_failed", "模型服务拒绝了当前凭据，请检查模型设置。"
    if "429" in detail or "rate limit" in detail or "too many requests" in detail:
        return "provider_rate_limited", "模型服务当前请求过多，请稍后重试。"
    if "timeout" in detail or "timed out" in detail:
        return "request_timeout", "模型响应超时，请重试。"
    if "model" in detail and any(token in detail for token in ("not found", "unknown", "invalid")):
        return "model_unavailable", "当前模型不可用，请检查模型设置。"
    if any(token in detail for token in ("connect", "network", "dns", "unavailable", "502", "503", "504")):
        return "provider_unavailable", "暂时无法连接模型服务，请稍后重试。"
    return "response_failed", "回复生成失败，请重试。"


class ChatTurnEventAdapter:
    """Transport adapter from EventBus input events to CompanionRuntime."""

    def __init__(self, companion_runtime, bus, gateway):
        self.bus = bus
        self.gateway = gateway
        self.companion_runtime = companion_runtime
        self.subscribed = False
        self._tasks: dict[tuple[str, int, str], asyncio.Task] = {}
        self._task_lock = asyncio.Lock()
        self._subscription_ids: list[int] = []
        self._dedupe_lock = asyncio.Lock()
        self._seen_request_ids: dict[str, float] = {}

    def start(self):
        if self.subscribed:
            return

        self._subscription_ids = [
            self.bus.subscribe(EventType.INPUT_TEXT, self.handle_input_text),
            self.bus.subscribe(EventType.CONTROL_INTERRUPT, self.handle_control),
            self.bus.subscribe(EventType.CONTROL_SESSION, self.handle_control),
        ]
        self.subscribed = True
        logger.info("Chat turn event adapter started")

    async def handle_input_text(self, event):
        packet = self._coerce_packet(event.data)
        if packet is None or await self._is_duplicate(packet):
            return

        packet.turn_id = packet.turn_id or packet.trace_id
        await self._cancel_matching(
            client_id=packet.client_id,
            session_id=packet.session_id,
        )

        key = self._packet_key(packet)
        async with self._task_lock:
            task = asyncio.create_task(
                self._process_input_text(packet),
                name=f"chat-turn:{packet.client_id}:{packet.turn_id}",
            )
            self._tasks[key] = task
            task.add_done_callback(
                lambda completed, turn_key=key: asyncio.create_task(
                    self._remove_task(turn_key, completed)
                )
            )

    async def handle_control(self, event):
        packet = self._coerce_packet(event.data)
        if packet is None:
            return
        if packet.source == "core.companion_runtime":
            return

        target_turn_id = packet.turn_id or (packet.payload or {}).get("turn_id")
        await self._cancel_matching(
            client_id=packet.client_id,
            session_id=packet.session_id,
            turn_id=target_turn_id,
        )

        result = await self.companion_runtime.handle_control_packet(packet)
        if result.get("action") == "reset":
            await self.gateway.publish_session_reset(
                packet.client_id,
                source="core.companion_runtime",
                turn_id=target_turn_id,
            )

    async def _process_input_text(self, packet):
        try:
            async for turn_event in self.companion_runtime.stream_text_packet(packet):
                await self._emit_turn_event(packet, turn_event)

        except asyncio.CancelledError:
            await self._emit_turn_event(
                packet,
                TurnStreamEvent(kind="ended", payload={"status": "interrupted"}),
            )
            raise
        except Exception as exc:
            logger.exception("Chat turn processing failed: %s", exc)
            session_id = packet.session_id
            code, message = classify_chat_error(exc)
            await self.bus.emit(
                EventType.SYSTEM_STATUS,
                EventPacket(
                    session_id=session_id,
                    client_id=packet.client_id,
                    turn_id=packet.turn_id,
                    generation=packet.generation,
                    type=EventType.SYSTEM_STATUS,
                    source="core.chat_turn",
                    payload={
                        "status": "error",
                        "code": code,
                        "message": message,
                        "details": str(exc),
                        "scope": "turn",
                    },
                ),
            )
            await self._emit_turn_event(
                packet,
                TurnStreamEvent(kind="ended", payload={"status": "failed"}),
            )

    def _coerce_packet(self, data):
        if isinstance(data, EventPacket):
            return data
        if isinstance(data, dict):
            return EventPacket(**data)
        return None

    async def _is_duplicate(self, packet: EventPacket) -> bool:
        async with self._dedupe_lock:
            current_time = asyncio.get_running_loop().time()
            cutoff = current_time - 30.0
            self._seen_request_ids = {
                request_id: seen_at
                for request_id, seen_at in self._seen_request_ids.items()
                if seen_at >= cutoff
            }
            request_key = f"{packet.client_id}:{packet.trace_id}"
            is_duplicate = request_key in self._seen_request_ids
            self._seen_request_ids[request_key] = current_time

        if is_duplicate:
            logger.warning("Duplicate chat request ignored: %s", packet.trace_id)
        return is_duplicate

    async def _emit_turn_event(self, packet: EventPacket, turn_event):
        event_type = {
            "started": EventType.BRAIN_THINKING,
            "delta": EventType.BRAIN_RESPONSE,
            "reasoning": EventType.BRAIN_REASONING,
            "ended": EventType.BRAIN_RESPONSE_END,
        }.get(turn_event.kind)

        if not event_type:
            logger.warning("Unknown chat turn event kind: %s", turn_event.kind)
            return

        await self.bus.emit(
            event_type,
            EventPacket(
                client_id=packet.client_id,
                turn_id=packet.turn_id,
                session_id=packet.session_id,
                generation=packet.generation,
                type=event_type,
                source="core.chat_turn",
                payload=turn_event.payload,
            ),
        )

    async def _cancel_matching(
        self,
        *,
        client_id: str,
        session_id: int,
        turn_id: str | None = None,
    ) -> None:
        await self.companion_runtime.interrupt(
            client_id=client_id,
            session_id=session_id,
            turn_id=turn_id,
        )
        async with self._task_lock:
            matches = [
                task
                for (active_client, active_session, active_turn), task in self._tasks.items()
                if active_client == client_id
                and active_session == session_id
                and (turn_id is None or active_turn == turn_id)
                and not task.done()
            ]
        for task in matches:
            task.cancel()
        if matches:
            await asyncio.gather(*matches, return_exceptions=True)

    async def _remove_task(
        self,
        key: tuple[str, int, str],
        task: asyncio.Task,
    ) -> None:
        async with self._task_lock:
            if self._tasks.get(key) is task:
                self._tasks.pop(key, None)

    async def stop(self) -> None:
        for subscription_id in self._subscription_ids:
            self.bus.unsubscribe(subscription_id)
        self._subscription_ids = []
        self.subscribed = False
        async with self._task_lock:
            tasks = [task for task in self._tasks.values() if not task.done()]
        for task in tasks:
            task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    @staticmethod
    def _packet_key(packet: EventPacket) -> tuple[str, int, str]:
        return (packet.client_id, packet.session_id, str(packet.turn_id))

    def _event_session_id(self, event) -> int:
        data = getattr(event, "data", None)
        if isinstance(data, EventPacket):
            return data.session_id
        if isinstance(data, dict):
            return int(data.get("session_id") or 0)
        return 0
