
import asyncio
import json
import logging
import uuid
from dataclasses import dataclass, field

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect

from core.events.bus import Event
from core.events.bus import EventBusError
from core.protocol import EventPacket, EventType
from routers.deps import get_gateway_service

logger = logging.getLogger("Gateway")
router = APIRouter(prefix="/lumina/gateway", tags=["Gateway"])

@dataclass
class GatewayConnection:
    websocket: WebSocket
    client_id: str
    session_id: int
    generation: int
    sequence_number: int = 0
    send_lock: asyncio.Lock = field(default_factory=asyncio.Lock)

    def next_sequence(self) -> int:
        self.sequence_number += 1
        return self.sequence_number


class GatewayService:
    """
    EventBus-driven Gateway.
    Acts as a bridge between WebSocket clients and the internal EventBus.
    """
    def __init__(self, bus):
        self._connections: dict[str, GatewayConnection] = {}
        self._session_snapshots: dict[str, tuple[int, int]] = {}
        self.bus = bus
        self._subscription_ids: list[int] = []
        self._subscribe_all()
        logger.info("GatewayService initialized")

    @property
    def active_connections(self) -> list[WebSocket]:
        return [state.websocket for state in self._connections.values()]

    def _subscribe_all(self):
        """Subscribe to all outbound events."""
        # We need to forward specific events to the frontend
        outbound_events = [
            EventType.BRAIN_THINKING,
            EventType.BRAIN_RESPONSE,
            EventType.BRAIN_REASONING,
            EventType.BRAIN_RESPONSE_END,
            EventType.COGNITIVE_STATE,
            EventType.SYSTEM_STATUS,
            EventType.CONTROL_SESSION,
            EventType.EMOTION_CHANGED,
        ]
        
        for event_type in outbound_events:
            self._subscription_ids.append(
                self.bus.subscribe(event_type, self.handle_outbound_event)
            )

    def bind_bus(self, bus) -> None:
        for subscription_id in self._subscription_ids:
            self.bus.unsubscribe(subscription_id)
        self._subscription_ids = []
        self.bus = bus
        self._subscribe_all()

    async def publish_session_reset(
        self,
        client_id: str,
        *,
        source: str = "system",
        turn_id: str | None = None,
    ) -> int:
        """Advance exactly one connected client's session generation."""
        state = self._connections.get(client_id)
        if state is None:
            raise KeyError(f"Gateway client is not connected: {client_id}")

        state.session_id += 1
        state.generation += 1
        state.sequence_number = 0
        self._session_snapshots[client_id] = (state.session_id, state.generation)
        await self._send_packet(
            state,
            EventPacket(
                client_id=client_id,
                turn_id=turn_id,
                session_id=state.session_id,
                generation=state.generation,
                type=EventType.CONTROL_SESSION,
                source="core.gateway",
                payload={
                    "session_id": state.session_id,
                    "generation": state.generation,
                    "client_id": client_id,
                    "action": "reset",
                    "requested_by": source,
                },
            ),
        )
        return state.session_id

    async def handle_outbound_event(self, event: Event):
        """
        Forward internal events to WebSocket.
        Expects event.data to be an EventPacket or a dict we can wrap.
        """
        if not self._connections:
            return

        packet: EventPacket
        if isinstance(event.data, EventPacket):
            packet = event.data
        elif isinstance(event.data, dict):
            packet = EventPacket(
                client_id=str(event.data.get("client_id") or ""),
                turn_id=event.data.get("turn_id"),
                session_id=int(event.data.get("session_id") or 0),
                generation=int(event.data.get("generation") or 0),
                type=event.type,
                source=event.source,
                payload=event.data,
            )
        else:
            packet = EventPacket(
                session_id=0,
                type=event.type,
                source=event.source,
                payload={"data": str(event.data)},
            )

        if packet.client_id:
            state = self._connections.get(packet.client_id)
            if state is not None:
                await self._send_packet(state, packet)
            return

        if packet.type not in {EventType.SYSTEM_STATUS, EventType.EMOTION_CHANGED}:
            logger.warning("Dropping unrouted gateway event type=%s", packet.type)
            return

        for state in list(self._connections.values()):
            await self._send_packet(state, packet)

    async def connect(self, websocket: WebSocket):
        if len(self._connections) >= 100:
            logger.warning("Gateway connection limit reached")
            await websocket.close(code=1013)
            return

        requested_client_id = str(websocket.query_params.get("client_id") or "").strip()
        client_id = requested_client_id or str(uuid.uuid4())
        session_id, generation = self._session_snapshots.get(client_id, (1, 1))

        await websocket.accept()
        previous = self._connections.pop(client_id, None)
        if previous is not None:
            await previous.websocket.close(code=1012)

        state = GatewayConnection(
            websocket=websocket,
            client_id=client_id,
            session_id=session_id,
            generation=generation,
        )
        self._connections[client_id] = state
        self._session_snapshots[client_id] = (session_id, generation)
        logger.info("Gateway client connected client_id=%s session=%s", client_id, session_id)
        await self._send_packet(
            state,
            EventPacket(
                client_id=client_id,
                session_id=session_id,
                generation=generation,
                type=EventType.CONTROL_SESSION,
                source="core.gateway",
                payload={
                    "action": "ready",
                    "client_id": client_id,
                    "session_id": session_id,
                    "generation": generation,
                },
            ),
        )
        
        # ... (init status)

        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    if len(data.encode("utf-8")) > 1024 * 1024:
                        await self._send_ack(
                            state,
                            request_id="unknown",
                            action="unknown",
                            status="rejected",
                            details="message_too_large",
                        )
                        continue
                    
                    # Handle raw ping first
                    if data == "ping":
                        await websocket.send_text("pong")
                        continue

                    json_data = {}
                    try:
                        json_data = json.loads(data)
                        packet = EventPacket(**json_data)
                    except (json.JSONDecodeError, ValueError) as exc:
                        logger.warning("Gateway rejected invalid packet bytes=%s: %s", len(data), exc)
                        await self._send_ack(
                            state,
                            request_id=str(json_data.get("trace_id") or "unknown"),
                            action=str(json_data.get("type") or "unknown"),
                            status="rejected",
                            details="invalid_packet",
                        )
                        continue
                    
                    logger.info(
                        "Gateway input type=%s source=%s bytes=%s",
                        packet.type,
                        packet.source,
                        len(data.encode("utf-8")),
                    )

                    request_id = packet.trace_id
                    packet.client_id = client_id
                    packet.session_id = state.session_id
                    packet.generation = state.generation
                    if packet.type == EventType.INPUT_TEXT:
                        packet.turn_id = packet.turn_id or request_id

                    try:
                        handlers = await self.bus.emit(
                            packet.type,
                            packet,
                            source="frontend",
                        )
                    except EventBusError as exc:
                        logger.warning("Gateway request dispatch failed: %s", exc)
                        await self._send_ack(
                            state,
                            request_id=request_id,
                            action=packet.type,
                            status="rejected",
                            details="dispatch_failed",
                            turn_id=packet.turn_id,
                        )
                        continue
                    if handlers <= 0:
                        await self._send_ack(
                            state,
                            request_id=request_id,
                            action=packet.type,
                            status="rejected",
                            details="no_handler",
                            turn_id=packet.turn_id,
                        )
                        continue

                    await self._send_ack(
                        state,
                        request_id=request_id,
                        action=packet.type,
                        status="accepted",
                        turn_id=packet.turn_id,
                    )

                except (WebSocketDisconnect, RuntimeError) as e:
                    logger.info(f"Client Disconnected ({type(e).__name__}): {e}")
                    break
                except Exception as e:
                    logger.exception("Gateway connection failed: %s", e)
                    break
                    
        finally:
            current = self._connections.get(client_id)
            if current is state:
                self._connections.pop(client_id, None)
            logger.info("Gateway client disconnected client_id=%s", client_id)

    async def _send_ack(
        self,
        state: GatewayConnection,
        *,
        request_id: str,
        action: str,
        status: str,
        details: str = "",
        turn_id: str | None = None,
    ) -> None:
        await self._send_packet(
            state,
            EventPacket(
                client_id=state.client_id,
                turn_id=turn_id,
                session_id=state.session_id,
                generation=state.generation,
                type=EventType.CONTROL_ACK,
                source="core.gateway",
                payload={
                    "request_id": request_id,
                    "status": status,
                    "action": action,
                    "details": details,
                },
            ),
        )

    async def _send_packet(
        self,
        state: GatewayConnection,
        packet: EventPacket,
    ) -> None:
        if packet.session_id not in {0, state.session_id}:
            return
        if packet.generation not in {0, state.generation}:
            return

        payload = packet.model_copy(
            update={
                "client_id": state.client_id,
                "session_id": state.session_id,
                "generation": state.generation,
                "sequence_number": state.next_sequence(),
            }
        ).model_dump()
        try:
            async with state.send_lock:
                await state.websocket.send_json(payload)
        except Exception as exc:
            logger.warning("Gateway send failed client_id=%s: %s", state.client_id, exc)

    async def close(self) -> None:
        for subscription_id in self._subscription_ids:
            self.bus.unsubscribe(subscription_id)
        self._subscription_ids = []
        connections = list(self._connections.values())
        self._connections.clear()
        for state in connections:
            try:
                await state.websocket.close(code=1001)
            except Exception:
                logger.debug("Gateway socket already closed client_id=%s", state.client_id)

@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    gateway_service: GatewayService = Depends(get_gateway_service),
):
    # [Security] Origin Check
    # Prevent CSWSH (Cross-Site WebSocket Hijacking)
    allowed_origins = ["http://localhost", "http://127.0.0.1", "app://", "file://"]
    origin = websocket.headers.get("origin", "").lower()
    
    if origin and not any(origin.startswith(ao) for ao in allowed_origins):
        logger.warning(f"🚨 Blocked WS Connection from invalid origin: {origin}")
        await websocket.close(code=1008)
        return

    # [Security] Token Authentication (Optional for Localhost, Required for Remote)
    token = websocket.query_params.get("token")
    if token:
        try:
            from security.tokens import TokenManager
            if not TokenManager.verify_token(token, expected_scope="runtime_client"):
                raise ValueError("invalid runtime client token")
        except Exception as e:
            logger.warning(f"🚨 WS Token Validation Failed: {e}")
            await websocket.close(code=1008)
            return

    await gateway_service.connect(websocket)

