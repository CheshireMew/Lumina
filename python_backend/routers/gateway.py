
import logging
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from core.protocol import EventPacket, EventType
from core.events.bus import get_event_bus, Event
import asyncio
import json

logger = logging.getLogger("Gateway")
router = APIRouter(prefix="/lumina/gateway", tags=["Gateway"])

class GatewayService:
    """
    EventBus-driven Gateway.
    Acts as a bridge between WebSocket clients and the internal EventBus.
    """
    def __init__(self):
        self.active_connections: list[WebSocket] = []
        self._session_id = 0 # Simple counter for now
        self.bus = get_event_bus()
        self._subscribe_all()

    def _subscribe_all(self):
        """Subscribe to all outbound events."""
        # We need to forward specific events to the frontend
        outbound_events = [
            EventType.BRAIN_THINKING,
            EventType.BRAIN_RESPONSE,
            "brain_response_end", # Custom string type
            EventType.COGNITIVE_STATE,
            EventType.SYSTEM_STATUS,
            EventType.CONTROL_SESSION,
            "emotion:changed"
        ]
        
        for evt in outbound_events:
            self.bus.subscribe(evt, self.handle_outbound_event)

    async def emit(self, packet):
        """Legacy compatibility: Emit to bus, which loopbacks to handle_outbound_event if subscribed."""
        # Note: If legacy code calls gateway.emit(packet), they expect it to go to WS.
        # We achieve this by publishing it to the bus.
        # Our own subscription will pick it up and send to WS.
        await self.bus.emit(packet.type, packet, source=packet.source)

    async def start_new_session(self, source="system"):
        """Legacy compatibility: Start new session and notify."""
        self._session_id += 1
        pkt = EventPacket(
            session_id=self._session_id,
            type=EventType.CONTROL_SESSION,
            source=source,
            payload={"session_id": self._session_id, "action": "start"}
        )
        # Emit so frontend gets it via handle_outbound_event
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
            # Try to extract session_id
            sid = event.data.get("session_id", 0)
            payload_to_send = EventPacket(
                session_id=sid,
                type=event.type,
                source=event.source,
                payload=event.data,
                timestamp=event.timestamp
            ).dict()
        else:
            logger.warning(f"Gateway received unknown data type for {event.type}: {type(event.data)}")
            return

        # Broadcast
        # logger.debug(f"Broadcasting {event.type} to {len(self.active_connections)} clients")
        for connection in self.active_connections:
            try:
                await connection.send_json(payload_to_send)
            except Exception as e:
                logger.error(f"Failed to send to WS: {e}")
                # Cleanup handled in 'connect' loop usually, but good to be safe

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"Client Connected [Session: {self._session_id}]")
        
        # Send Initial Status
        try:
            init_packet = EventPacket(
                session_id=self._session_id,
                type=EventType.SYSTEM_STATUS,
                source="gateway",
                payload={"status": "connected", "session_id": self._session_id}
            )
            await websocket.send_json(init_packet.dict())
        except Exception as e:
            logger.error(f"Failed to send init packet: {e}")
            return

        try:
            while True:
                try:
                    data = await websocket.receive_text()
                    
                    # Handle raw ping first
                    if data == "ping":
                        await websocket.send_text("pong")
                        continue

                    # Log raw data for debugging
                    logger.info(f"RAW WS RECV: {data[:200]}")
                    
                    try:
                        json_data = json.loads(data)
                    except json.JSONDecodeError:
                        logger.warning(f"Gateway received invalid JSON: {data[:50]}...")
                        continue
                    
                    logger.info(f"GATEWAY INPUT: {json_data.get('type')} from {json_data.get('source')}")
                    
                    # Parse Packet
                    packet = EventPacket(**json_data)
                    
                    # Routing
                    if packet.type == "session_control" or packet.type == EventType.CONTROL_SESSION:
                         # Forward to system (e.g. for clearing context)
                         await self.bus.emit(EventType.CONTROL_SESSION, packet, source="frontend") 
                    elif packet.type == EventType.INPUT_TEXT or packet.type == "chat":
                        print("DEBUG: Gateway Emitting INPUT_TEXT")
                        # Publish to Bus (normalize to INPUT_TEXT)
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
    await gateway_service.connect(websocket)

