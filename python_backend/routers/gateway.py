
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.protocol import EventPacket, EventType
from core.events.bus import get_event_bus, Event
import json

logger = logging.getLogger("Gateway")
router = APIRouter(prefix="/lumina/gateway", tags=["Gateway"])

class GatewayService:
    """
    EventBus-driven Gateway.
    Acts as a bridge between WebSocket clients and the internal EventBus.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GatewayService, cls).__new__(cls)
            cls._instance.initialized = False
        return cls._instance

    def __init__(self):
        if self.initialized:
            return
        self.initialized = True
        
        self.active_connections: list[WebSocket] = []
        self._session_id = 0 
        self._sequences: dict[int, int] = {} # [Architecture 4.2] Per-session sequence tracker
        self.bus = get_event_bus()
        self._subscribe_all()
        logger.info("✅ GatewayService Initialized (Singleton)")

    def _get_next_sequence(self, session_id: int) -> int:
        """Increment and return the next sequence number for a session."""
        current = self._sequences.get(session_id, 0)
        next_seq = current + 1
        self._sequences[session_id] = next_seq
        return next_seq

    def _subscribe_all(self):
        """Subscribe to all outbound events."""
        # We need to forward specific events to the frontend
        outbound_events = [
            EventType.BRAIN_THINKING,
            EventType.BRAIN_RESPONSE,
            EventType.BRAIN_RESPONSE_END,
            EventType.COGNITIVE_STATE,
            EventType.SYSTEM_STATUS,
            EventType.CONTROL_SESSION,
            EventType.EMOTION_CHANGED,
        ]
        
        for evt in outbound_events:
            self.bus.subscribe(evt, self.handle_outbound_event)

    async def publish_session_reset(self, source="system"):
        """Start a new frontend interaction session after context reset."""
        self._session_id += 1
        pkt = EventPacket(
            session_id=self._session_id,
            type=EventType.CONTROL_SESSION,
            source=source,
            payload={"session_id": self._session_id, "action": "start"}
        )
        await self.bus.emit(pkt.type, pkt, source=source)
        return self._session_id

    async def handle_outbound_event(self, event: Event):
        """
        Forward internal events to WebSocket.
        Expects event.data to be an EventPacket or a dict we can wrap.
        """
        if not self.active_connections:
            return

        payload_to_send = None
        
        # 1. If data is already EventPacket, send as is
        if isinstance(event.data, EventPacket):
            payload_to_send = event.data.dict()
        # 2. If data is dict, wrap it
        elif isinstance(event.data, dict):
            # Try to extract session_id from the dict data
            sid = event.data.get("session_id", 0)
            payload_to_send = EventPacket(
                session_id=sid,
                type=event.type,
                source=event.source,
                payload=event.data,
                timestamp=event.timestamp
            ).dict()
        else:
            # Fallback for other types (e.g. strings)
            # Create a generic packet
            payload_to_send = EventPacket(
                session_id=0,
                type=event.type,
                source=event.source,
                payload={"data": str(event.data)},
                timestamp=event.timestamp
            ).dict()

        # [Architecture 4.2] Tier C: Sequence Injection
        sid = payload_to_send.get("session_id", 0)
        payload_to_send["sequence_number"] = self._get_next_sequence(sid)

        # Broadcast
        # logger.debug(f"Broadcasting {event.type} (# {payload_to_send['sequence_number']}) to {len(self.active_connections)} clients")
        for connection in self.active_connections:
            try:
                await connection.send_json(payload_to_send)
            except Exception as e:
                logger.error(f"Failed to send to WS: {e}")
                # Cleanup handled in 'connect' loop usually, but good to be safe

    async def connect(self, websocket: WebSocket):
        # [Security] Connection Limit
        if len(self.active_connections) > 100:
             logger.warning("🚨 Gateway Connection Limit Reached (100). Rejecting.")
             await websocket.close(code=1013) # Try Again Later
             return

        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client Connected [Session: {self._session_id}]")
        
        # ... (init status)

        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    # [Security] Message Size Limit (5MB)
                    # Prevents memory exhaustion attacks
                    if len(data) > 5 * 1024 * 1024:
                         logger.warning("🚨 WS Message too large. Dropping.")
                         continue
                    
                    # ... (rest of loop)
                    
                    # Handle raw ping first
                    if data == "ping":
                        await websocket.send_text("pong")
                        continue

                    # Log raw data for debugging (Masked)
                    preview = data[:50] + "..." if len(data) > 50 else data
                    logger.debug(f"RAW WS RECV: {preview}")
                    
                    try:
                        json_data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Gateway received invalid JSON: {data[:50]}...")
                        continue
                    
                    logger.info(f"GATEWAY INPUT: {json_data.get('type')} from {json_data.get('source')}")
                    
                    # Parse Packet
                    packet = EventPacket(**json_data)
                    
                    # Routing
                    if packet.type == EventType.CONTROL_SESSION:
                         # Forward to system (e.g. for clearing context)
                         await self.bus.emit(EventType.CONTROL_SESSION, packet, source="frontend") 
                    elif packet.type == EventType.INPUT_TEXT:
                        logger.debug("Gateway Emitting INPUT_TEXT")
                        packet.type = EventType.INPUT_TEXT
                        await self.bus.emit(EventType.INPUT_TEXT, packet, source="frontend")
                    elif packet.type == EventType.INPUT_AUDIO:
                        await self.bus.emit(EventType.INPUT_AUDIO, packet, source="frontend")
                    else:
                        await self.bus.emit(packet.type, packet, source="frontend")

                except (WebSocketDisconnect, RuntimeError) as e:
                    logger.info(f"Client Disconnected ({type(e).__name__}): {e}")
                    break
                except json.JSONDecodeError:
                    logger.warning("Gateway received invalid JSON")
                    continue
                except Exception as e:
                    logger.error(f"Error processing message: {e}")
                    break
                    
        finally:
            logger.info("Cleaning up connection...")
            if websocket in self.active_connections:
                self.active_connections.remove(websocket)

# Singleton
gateway_service = GatewayService()

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
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
            if not TokenManager.verify_token(token, expected_scope="plugin"):
                raise ValueError("invalid plugin token")
        except Exception as e:
            logger.warning(f"🚨 WS Token Validation Failed: {e}")
            await websocket.close(code=1008)
            return

    await gateway_service.connect(websocket)

