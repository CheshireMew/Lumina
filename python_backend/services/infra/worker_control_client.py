"""
Worker Control Client (Worker Process Side).
Connects to Main Process WebSocket and handles bidirectional communication.
"""

import asyncio
import logging
import time
from typing import Callable, List, Dict, Any, Optional
import websockets
from websockets.exceptions import ConnectionClosed, InvalidStatusCode

from core.protocols.worker_control import (
    ConfigUpdatePayload, LifecyclePayload, WsMessage, WsMessageType, ProviderStatusPayload
)
from pydantic import ValidationError
from services.observability.structured_logger import set_log_context, reset_log_context

logger = logging.getLogger("WorkerControlClient")


class WorkerControlClient:
    """
    WebSocket client for Worker-to-Main communication.
    Handles:
    - Registration with Main
    - Periodic heartbeat and status reports
    - Receiving config updates and lifecycle commands
    - Auto-reconnection with exponential backoff
    """
    
    def __init__(
        self,
        worker_id: str,
        worker_type: str,
        main_port: int,
        worker_port: int,
        runtime_target: str | None = None,
        main_host: str = "127.0.0.1",
        heartbeat_interval: int = 15,
        status_provider: Callable[[], List[Dict[str, Any]]] = None
    ):
        self.worker_id = worker_id
        self.worker_type = worker_type
        self.runtime_target = runtime_target
        self.main_host = main_host
        self.main_port = main_port
        self.worker_port = worker_port
        self.heartbeat_interval = heartbeat_interval
        self.status_provider = status_provider
        
        self._ws: Optional[websockets.WebSocketClientProtocol] = None
        self._running = False
        self._connected = False
        self._reconnect_delay = 1.0
        self._max_reconnect_delay = 60.0
        self._start_time = time.time()
        
        # Event handlers
        self._config_handler: Optional[Callable] = None
        self._lifecycle_handler: Optional[Callable] = None
        
        # Tasks
        self._connection_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._receive_task: Optional[asyncio.Task] = None
    
    @property
    def is_connected(self) -> bool:
        return self._connected and self._ws is not None
    
    @property
    def ws_url(self) -> str:
        import os
        base = f"ws://{self.main_host}:{self.main_port}/ws/worker-control"
        token = os.environ.get("LUMINA_WORKER_TOKEN")
        if token:
            return f"{base}?token={token}"
        return base
    
    # --- Lifecycle ---
    
    def start(self):
        """Start the WebSocket client (non-blocking)."""
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._connection_task = asyncio.create_task(self._connection_loop())
        logger.info(f"🚀 WorkerControlClient started for {self.worker_id}")
    
    async def stop(self):
        """Stop the WebSocket client gracefully."""
        self._running = False

        websocket = self._ws
        self._ws = None
        if websocket:
            try:
                await websocket.close()
            except ConnectionClosed:
                pass

        tasks = [
            task
            for task in (self._heartbeat_task, self._receive_task, self._connection_task)
            if task is not None
        ]
        for task in tasks:
            if not task.done():
                task.cancel()
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

        self._heartbeat_task = None
        self._receive_task = None
        self._connection_task = None
        
        self._connected = False
        logger.info("🛑 WorkerControlClient stopped")
    
    # --- Connection Management ---
    
    async def _connection_loop(self):
        """Main connection loop with auto-reconnect."""
        while self._running:
            try:
                await self._connect_and_run()
            except (ConnectionClosed, ConnectionRefusedError, OSError) as e:
                self._connected = False
                if self._running:
                    logger.warning(f"Connection lost: {e}. Reconnecting in {self._reconnect_delay:.1f}s...")
                    await asyncio.sleep(self._reconnect_delay)
                    self._reconnect_delay = min(self._reconnect_delay * 2, self._max_reconnect_delay)
            except InvalidStatusCode as e:
                self._connected = False
                logger.error(f"WebSocket connection rejected: {e}")
                await asyncio.sleep(self._reconnect_delay)
            except asyncio.CancelledError:
                break
            except Exception as e:
                self._connected = False
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(self._reconnect_delay)
    
    async def _connect_and_run(self):
        """Establish connection and run message loops."""
        logger.info(f"🔗 Connecting to {self.ws_url}...")
        
        async with websockets.connect(self.ws_url) as ws:
            self._ws = ws
            self._reconnect_delay = 1.0  # Reset backoff on successful connect
            
            # Send registration
            reg_msg = WsMessage.register(
                worker_id=self.worker_id,
                worker_type=self.worker_type,
                port=self.worker_port,
                runtime_target=self.runtime_target,
            )
            await ws.send(reg_msg.model_dump_json())
            
            # Wait for ACK
            ack_raw = await asyncio.wait_for(ws.recv(), timeout=10.0)
            ack = WsMessage.model_validate_json(ack_raw)
            if ack.type != WsMessageType.ACK:
                raise Exception(f"Expected ACK, got {ack.type}")
            
            self._connected = True
            logger.info(f"✅ Connected to Main, session={ack.session_id}")
            
            # Start heartbeat and receive tasks
            self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
            self._receive_task = asyncio.create_task(self._receive_loop())
            
            # Wait for either task to complete (disconnect)
            done, pending = await asyncio.wait(
                [self._heartbeat_task, self._receive_task],
                return_when=asyncio.FIRST_COMPLETED
            )
            
            # Cancel remaining tasks
            for task in pending:
                task.cancel()
            if pending:
                await asyncio.gather(*pending, return_exceptions=True)
    
    # --- Heartbeat & Status ---
    
    async def _heartbeat_loop(self):
        """Send periodic heartbeat with status."""
        while self._running and self._connected:
            try:
                await self._send_status()
            except Exception as e:
                logger.warning(f"Heartbeat send failed: {e}")
            await asyncio.sleep(self.heartbeat_interval)
    
    async def _send_status(self):
        """Send detailed status report."""
        if not self._ws or not self._connected:
            return
        
        # Get system load
        load = self._get_system_load()
        uptime = time.time() - self._start_time
        
        # Get provider status
        providers = []
        if self.status_provider:
            try:
                if asyncio.iscoroutinefunction(self.status_provider):
                    raw_providers = await self.status_provider()
                else:
                    raw_providers = self.status_provider()
                
                for p in raw_providers:
                    active_status = p.get("active_status")
                    computed_status = p.get("computed_status")
                    providers.append(ProviderStatusPayload(
                        id=p.get("id", "unknown"),
                        name=p.get("name", p.get("id", "unknown")),
                        enabled=bool(p.get("enabled", True)),
                        status=computed_status or active_status or p.get("status", "unknown"),
                        kind=p.get("kind"),
                        category=p.get("category", "other"),
                        desired_enabled=p.get("desired_enabled"),
                        active=p.get("active"),
                        active_status=active_status,
                        computed_status=computed_status,
                        group_id=p.get("group_id"),
                        group_policy=p.get("group_policy"),
                        active_in_group=p.get("active_in_group"),
                        version=p.get("version"),
                        capability=p.get("capability") or p.get("group_id"),
                        capabilities=p.get("capabilities", []),
                        runtime_target=p.get("runtime_target"),
                        config_schema=p.get("config_schema"),
                        current_config=p.get("current_config"),
                        error=p.get("error"),
                        load_time_ms=p.get("load_time_ms"),
                        service_url=p.get("service_url"),
                        driver_id=p.get("driver_id"),
                    ))
            except Exception as e:
                logger.warning(f"Status provider error: {e}")
        
        msg = WsMessage.status(
            worker_id=self.worker_id,
            providers=providers,
            load=load,
            uptime=uptime
        )
        await self._ws.send(msg.model_dump_json())
    
    def _get_system_load(self) -> float:
        """Get current system load (0.0 - 1.0)."""
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None) / 100.0
            mem = psutil.virtual_memory().percent / 100.0
            return max(cpu, mem)
        except ImportError:
            return 0.1
        except Exception:
            return 0.0
    
    def send_binary(self, msg: WsMessage, binary_body: bytes):
        """Send a binary message (Header + Body)."""
        if not self._ws or not self._connected:
            # Drop silently or log?
            return
        
        try:
            payload = msg.pack_binary(binary_body)
            # websocket.send() handles bytes automatically
            asyncio.create_task(self._ws.send(payload))
        except Exception as e:
            logger.error(f"Failed to send binary: {e}")

    # --- Receiving Messages ---
    
    async def _receive_loop(self):
        """Receive and dispatch messages from Main (Text/JSON or Binary)."""
        while self._running and self._ws:
            try:
                raw = await self._ws.recv()
                
                if isinstance(raw, str):
                    # JSON Path
                    msg = WsMessage.model_validate_json(raw)
                    await self._handle_message(msg)
                elif isinstance(raw, bytes):
                    # Binary Path (v1.5)
                    msg, body = WsMessage.unpack_binary(raw)
                    await self._handle_message(msg, binary_body=body)
                    
            except ValidationError as e:
                logger.warning(f"Invalid message: {e}")
            except ConnectionClosed:
                if self._running:
                    raise
                break
            except Exception as e:
                logger.error(f"Receive error: {e}")

    async def _handle_message(self, msg: WsMessage, binary_body: bytes = None):
        """Handle incoming message from Main."""
        if msg.trace_id:
            tokens = set_log_context(trace_id=msg.trace_id)
        else:
            tokens = {}
        
        try:
            if msg.type == WsMessageType.CONFIG_UPDATE:
                payload = ConfigUpdatePayload.model_validate(msg.payload)
                logger.info(f"📥 Config update received: section={payload.section}")
                if self._config_handler:
                    try:
                        if asyncio.iscoroutinefunction(self._config_handler):
                            await self._config_handler(payload)
                        else:
                            self._config_handler(payload)
                    except Exception as e:
                        logger.error(f"Config handler error: {e}")
            
            elif msg.type == WsMessageType.LIFECYCLE:
                payload = LifecyclePayload.model_validate(msg.payload)
                logger.info(f"📥 Lifecycle command: {payload.action} -> {payload.target_id}")
                if self._lifecycle_handler:
                    try:
                        if asyncio.iscoroutinefunction(self._lifecycle_handler):
                            await self._lifecycle_handler(payload)
                        else:
                            self._lifecycle_handler(payload)
                    except Exception as e:
                        logger.error(f"Lifecycle handler error: {e}")
            
            elif msg.type == WsMessageType.ERROR:
                payload_keys = sorted(msg.payload) if isinstance(msg.payload, dict) else []
                logger.warning("Error response received from Main (fields=%s)", payload_keys)
        finally:
            if tokens:
                reset_log_context(tokens)
    
    # --- Event Handlers ---
    
    def on_config_update(self, handler: Callable):
        """Register handler for config update messages."""
        self._config_handler = handler
    
    def on_lifecycle(self, handler: Callable):
        """Register handler for lifecycle messages."""
        self._lifecycle_handler = handler



