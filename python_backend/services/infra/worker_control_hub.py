"""
Worker Control Hub (Main Process Side).
Manages WebSocket connections from all Worker processes.
"""

import asyncio
import logging
import time
from typing import Dict, Optional, Callable, List, Any
from fastapi import WebSocket, WebSocketDisconnect
from pydantic import ValidationError

from services.observability.structured_logger import trace_id_ctx


from core.protocols.worker_control import (
    WsMessage, WsMessageType, 
    StatusPayload, HeartbeatPayload, WorkerRegisterPayload
)
from core.runtime import normalize_runtime_target

logger = logging.getLogger("WorkerControlHub")


class WorkerConnection:
    """Represents a connected worker."""
    def __init__(self, worker_id: str, worker_type: str, runtime_target: str, websocket: WebSocket, port: int):
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.runtime_target = runtime_target
        self.websocket = websocket
        self.port = port
        self.connected_at = time.time()
        self.last_heartbeat = time.time()
        self.load = 0.0
        self.status = "healthy"
        self.providers: List[Dict[str, Any]] = []


class WorkerControlHub:
    """
    Central hub for managing Worker WebSocket connections.
    Main-process control channel for worker runtimes.
    """
    def __init__(self, discovery):
        self.discovery = discovery
        self._workers: Dict[str, WorkerConnection] = {}
        self._message_handlers: Dict[WsMessageType, List[Callable]] = {}
        self._cleanup_task: Optional[asyncio.Task] = None
        self._heartbeat_timeout = 45  # seconds (3x heartbeat interval)
        
        logger.info("🎛️ WorkerControlHub initialized")
    
    # --- Connection Management ---
    
    async def handle_connection(self, websocket: WebSocket):
        """Handle a new WebSocket connection from a worker."""
        # [Security] Verify worker JWT before accepting
        token = websocket.query_params.get("token")
        if token:
            from security.tokens import TokenManager
            payload = TokenManager.verify_token(token, expected_scope="worker")
            if not payload:
                logger.warning(f"🚫 Worker connection rejected: invalid token")
                await websocket.close(code=4001, reason="Unauthorized")
                return
        else:
            # No token provided — reject unless in dev mode
            from app_config import IS_DEV
            if not IS_DEV:
                logger.warning("🚫 Worker connection rejected: no token (production mode)")
                await websocket.close(code=4001, reason="Unauthorized")
                return
            logger.debug("⚠️ Worker connection accepted without token (dev mode)")

        await websocket.accept()
        
        worker_id = None
        try:
            # Wait for registration message
            raw = await asyncio.wait_for(websocket.receive_json(), timeout=10.0)
            msg = WsMessage.model_validate(raw)
            
            if msg.type != WsMessageType.REGISTER:
                await websocket.send_json(WsMessage.error("Expected REGISTER message").model_dump())
                await websocket.close()
                return
            
            reg = WorkerRegisterPayload.model_validate(msg.payload)
            worker_id = reg.worker_id
            
            # Store connection
            self._workers[worker_id] = WorkerConnection(
                worker_id=worker_id,
                worker_type=reg.worker_type,
                runtime_target=normalize_runtime_target(reg.runtime_target or reg.worker_id),
                websocket=websocket,
                port=reg.port
            )

            try:
                self.discovery.register(
                    worker_id=worker_id,
                    host=reg.host,
                    port=reg.port,
                    capabilities=[reg.worker_type],
                    runtime_target=reg.runtime_target or reg.worker_id,
                )
            except Exception as exc:
                logger.debug(f"Failed to register discovery node for {worker_id}: {exc}")
            
            logger.info(f"✅ Worker connected: {worker_id} ({reg.worker_type}:{reg.port})")
            
            # Send ACK
            await websocket.send_json(WsMessage.ack(session_id=worker_id).model_dump())
            
            # Message loop
            await self._message_loop(worker_id, websocket)
            
        except asyncio.TimeoutError:
            logger.warning("Worker connection timed out waiting for REGISTER")
            await websocket.close()
        except WebSocketDisconnect:
            if worker_id:
                logger.info(f"📤 Worker disconnected: {worker_id}")
        except ValidationError as e:
            logger.warning(f"Invalid message format: {e}")
            await websocket.close()
        except Exception as e:
            logger.error(f"Worker connection error: {e}")
        finally:
            if worker_id and worker_id in self._workers:
                del self._workers[worker_id]
    
    async def _message_loop(self, worker_id: str, websocket: WebSocket):
        """Process messages from a connected worker (Text/JSON or Binary)."""
        import json
        while True:
            try:
                # Use raw receive to support both Text and Binary frames
                message = await websocket.receive()
                
                if message["type"] == "websocket.disconnect":
                    # Raise Disconnect to trigger cleanup in handle_connection
                    raise WebSocketDisconnect(message.get("code", 1000))
                
                if "text" in message and message["text"]:
                    # 1. Start JSON Path
                    payload = json.loads(message["text"])
                    msg = WsMessage.model_validate(payload)
                    await self._dispatch_message(worker_id, msg)
                    
                elif "bytes" in message and message["bytes"]:
                    # 2. Binary Path (v1.5)
                    msg, body = WsMessage.unpack_binary(message["bytes"])
                    await self._dispatch_message(worker_id, msg, binary_body=body)
                    
            except WebSocketDisconnect:
                raise # Re-raise to break loop and trigger cleanup
            except ValidationError as e:
                logger.warning(f"Invalid message from {worker_id}: {e}")
            except Exception as e:
                logger.error(f"Message processing error from {worker_id}: {e}")
                # Don't break loop on parse error, just log
    
    async def _dispatch_message(self, worker_id: str, msg: WsMessage, binary_body: bytes = None):
        """Dispatch message to appropriate handler."""
        worker = self._workers.get(worker_id)
        if not worker:
            return
        
        # Import metrics (late import to avoid circular deps)
        try:
            from services.observability.metrics import update_worker_status, ACTIVE_WORKERS
        except ImportError:
            update_worker_status = None
            ACTIVE_WORKERS = None
        
        if msg.type == WsMessageType.HEARTBEAT:
            payload = HeartbeatPayload.model_validate(msg.payload)
            worker.last_heartbeat = time.time()
            worker.load = payload.load
            logger.debug(f"💓 Heartbeat from {worker_id}, load={payload.load:.2f}")
            
            # Update metrics
            if update_worker_status:
                update_worker_status(worker_id, worker.worker_type, payload.load)
            
        elif msg.type == WsMessageType.STATUS:
            payload = StatusPayload.model_validate(msg.payload)
            worker.last_heartbeat = time.time()
            worker.load = payload.load
            worker.status = payload.status
            worker.providers = [p.model_dump() if hasattr(p, 'model_dump') else p for p in payload.providers]
            logger.debug(f"📊 Status from {worker_id}: {len(payload.providers)} providers")

            # Update metrics
            if update_worker_status:
                update_worker_status(worker_id, worker.worker_type, payload.load)

            try:
                self.discovery.register(
                    worker_id=worker_id,
                    host="127.0.0.1",
                    port=worker.port,
                    capabilities=[worker.worker_type],
                    runtime_target=worker.runtime_target,
                )
            except Exception as exc:
                logger.debug(f"Failed to refresh discovery node for {worker_id}: {exc}")

        
        # Call registered handlers
        handlers = self._message_handlers.get(msg.type, [])
        for handler in handlers:
            try:
                if asyncio.iscoroutinefunction(handler):
                    await handler(worker_id, msg, binary_body=binary_body)
                else:
                    handler(worker_id, msg, binary_body=binary_body)
            except Exception as e:
                logger.error(f"Handler error for {msg.type}: {e}")
    
    # --- Sending Messages ---
    
    async def send_to_worker(self, worker_id: str, msg: WsMessage) -> bool:
        """Send a message to a specific worker."""
        worker = self._workers.get(worker_id)
        if not worker:
            logger.warning(f"Worker {worker_id} not connected")
            return False
        
        try:
            # Inject trace_id
            msg.trace_id = trace_id_ctx.get()
            await worker.websocket.send_json(msg.model_dump())
            return True
        except Exception as e:
            logger.error(f"Failed to send to {worker_id}: {e}")
            return False
    
    async def broadcast(self, msg: WsMessage, worker_type: str = None, runtime_target: str = None) -> int:
        """
        Broadcast a message to all workers (or filtered by type).
        Returns number of workers that received the message.
        """
        sent = 0
        normalized_target = normalize_runtime_target(runtime_target) if runtime_target else None
        for wid, worker in list(self._workers.items()):
            if worker_type and worker.worker_type != worker_type:
                continue
            if normalized_target and normalize_runtime_target(worker.runtime_target) != normalized_target:
                continue
            try:
                # Inject trace_id
                msg.trace_id = trace_id_ctx.get()
                await worker.websocket.send_json(msg.model_dump())
                sent += 1
            except Exception as e:
                logger.warning(f"Broadcast to {wid} failed: {e}")
        return sent
    
    async def broadcast_config_update(self, data: Dict[str, Any], section: str = None, runtime_target: str = None):
        """Convenience: Broadcast config update to all workers."""
        msg = WsMessage.config_update(data=data, section=section)
        count = await self.broadcast(msg, runtime_target=runtime_target)
        logger.info(f"📢 Config update broadcasted to {count} workers")
    
    async def broadcast_lifecycle(self, action: str, target_id: str, runtime_target: str = None):
        """Convenience: Broadcast lifecycle command to all workers."""
        msg = WsMessage.lifecycle(action=action, target_id=target_id)
        count = await self.broadcast(msg, runtime_target=runtime_target)
        logger.info(f"📢 Lifecycle [{action}:{target_id}] broadcasted to {count} workers")
    
    # --- Query ---
    
    def get_worker(self, worker_id: str) -> Optional[WorkerConnection]:
        return self._workers.get(worker_id)
    
    def get_all_workers(self) -> Dict[str, WorkerConnection]:
        return dict(self._workers)
    
    def is_worker_connected(self, worker_id: str) -> bool:
        return worker_id in self._workers
    
    # --- Event Handlers ---
    
    def on_message(self, msg_type: WsMessageType, handler: Callable):
        """Register a handler for a specific message type."""
        if msg_type not in self._message_handlers:
            self._message_handlers[msg_type] = []
        self._message_handlers[msg_type].append(handler)
    
    # --- Cleanup ---
    
    def start_cleanup_task(self):
        """Start background task to clean up stale connections."""
        if self._cleanup_task is None:
            self._cleanup_task = asyncio.create_task(self._cleanup_loop())
    
    async def _cleanup_loop(self):
        """Remove workers that haven't sent heartbeat in timeout period."""
        while True:
            await asyncio.sleep(30)

            now = time.time()
            stale = [
                wid for wid, w in self._workers.items()
                if (now - w.last_heartbeat) > self._heartbeat_timeout
            ]
            for wid in stale:
                logger.warning(f"⚠️ Worker {wid} timed out, removing")
                try:
                    await self._workers[wid].websocket.close()
                except Exception as e:
                    logger.debug(f"Error closing stale websocket for {wid}: {e}")
                del self._workers[wid]
    
    async def shutdown(self):
        """Gracefully shut down all connections."""
        if self._cleanup_task:
            self._cleanup_task.cancel()
        
        for wid, worker in list(self._workers.items()):
            try:
                await worker.websocket.close()
            except Exception as e:
                logger.debug(f"Error closing websocket for {wid}: {e}")
        self._workers.clear()
        logger.info("🛑 WorkerControlHub shutdown complete")
