"""
RemotePluginProxy: Runs in the Main Process.
Acts as a bridge to the isolated child process.
"""
import uuid
import logging
import asyncio
import multiprocessing
import json
import time
from typing import Optional, Any
from core.interfaces.plugin import BaseSystemPlugin
from core.manifest import PluginManifest
from core.isolation.host import host_entrypoint

logger = logging.getLogger("RemoteProxy")

class RemoteContextStub:
    """
    Minimally viable context for child process.
    Allows plugin to emit events back to parent.
    """
    def __init__(self, event_queue, plugin_id):
        self.bus = self
        self._queue = event_queue
        self.plugin_id = plugin_id

    async def emit(self, event_type: str, payload: Any = None):
        """Standard EventBus.emit interface"""
        # Support both (event_obj) and (type, payload) usage
        if hasattr(event_type, "type") and payload is None:
            # It's an EventPacket object
            evt = event_type
            data = evt.dict() if hasattr(evt, 'dict') else evt
            self._queue.put({"type": "emit", "event": data})
        else:
            # (str, dict) usage
            event_dict = {
                "type": event_type,
                "payload": payload or {}
            }
            self._queue.put({"type": "emit", "event": event_dict})

    def emit_sync(self, topic, payload):
        """Synchronous emit for shared plugin compatibility."""
        # Wrap in expected event structure
        event_dict = {
            "type": topic, # Use 'type' to match EventBus event structure
            "payload": payload
        }
        self._queue.put({"type": "emit", "event": event_dict})

    def subscribe(self, topic, handler):
        # TODO: Implement reverse subscription (Main -> Child)
        pass

    def register_service(self, name, service):
        # Notify Parent to register the Proxy as the service
        self._queue.put({"type": "sys.register", "name": name})
        logging.info(f"📨 Service '{name}' registration forwarded to Main Process.")

    def get_data_dir(self, plugin_id: str = None) -> Optional[str]:
        # Return injected data dir
        if hasattr(self, '_data_dir') and self._data_dir:
             from pathlib import Path
             return Path(self._data_dir)
        return None

    def register_route_def(self, path: str, method: str, handler_name: str, handler: Any):
        """
        Forward generic route registration to the parent process.
        The parent (RemotePluginProxy) will intercept this event and mount an RPC stub.
        """
        payload = {
            "plugin_id": self.plugin_id,
            "path": path,
            "method": method,
            "handler_name": handler_name,
            # "handler" is not sent (cannot be pickled easily across processes), parent creates stub
        }
        
        # Mimic Event structure
        event_dict = {
            "type": "core.register_route_def", # FIXED: Was 'topic'
            "payload": payload
        }
        
        self._queue.put({"type": "emit", "event": event_dict})
        logging.info(f"📨 Route '{method} {path}' registration forwarded to Main Process.")

    def emit_log(self, record_dict):
        """
        [PR-3] Forward Log Record from Child to Parent.
        """
        self._queue.put({
            "type": "log",
            "record": record_dict
        })


class RPCStream:
    """Helper to consume RPC stream chunks as an async iterator"""
    def __init__(self):
        self.queue = asyncio.Queue()
        self.finished = False
        
    def __aiter__(self):
        return self
        
    async def __anext__(self):
        if self.finished and self.queue.empty():
            raise StopAsyncIteration
            
        item = await self.queue.get()
        if item is StopAsyncIteration:
            self.finished = True
            raise StopAsyncIteration
        return item
        
    def push(self, chunk):
        self.queue.put_nowait(chunk)
        
    def close(self):
        self.queue.put_nowait(StopAsyncIteration)


class RemotePluginProxy(BaseSystemPlugin):
    # ... (Keep existing __init__ etc) ...
    
    # We need to store active streams to routes chunks to them
    # _active_streams: Dict[req_id, RPCStream]
    
    def __init__(self, manifest_data: dict):
        super().__init__() # Ensure Base Init if needed (though Base is ABC)
        self._manifest_data = manifest_data
        self._manifest_obj = PluginManifest(**manifest_data)
        
        self.ipc_queue = multiprocessing.Queue()
        self.event_queue = multiprocessing.Queue()
        self.process: Optional[multiprocessing.Process] = None
        self.context = None 
        
        self._pending_requests: Dict[str, asyncio.Future] = {}
        self._active_streams: Dict[str, RPCStream] = {} # [PR-4]
        self._child_subscriptions: set = set()  # [Phase 1] Topics child process subscribed to

    # ... (Properties) ...
    # Skip to _event_loop modification
    
    # ... (inside class) ...

        
        # [REMOVED] Router Support (Simplified Architecture)
        # We no longer attempt to dynamic import routers for isolated plugins.
        # Plugins requiring API routes should run in 'local' mode.

    @property
    def id(self) -> str:
        return self._manifest_obj.id

    @property
    def name(self) -> str:
        return self._manifest_obj.name

    @property
    def enabled(self): return True # Managed by Manager
    
    @enabled.setter
    def enabled(self, v): pass 

    @property
    def config_schema(self):
        """
        [Phase 3] Read config_schema from manifest instead of returning None.
        This allows frontend to render configuration UI for isolated plugins.
        """
        return getattr(self._manifest_obj, 'config_schema', None)

    @property
    def _manifest(self):
        return self._manifest_obj

    def get_status(self) -> dict:
        """
        Safe get_status that avoids __getattr__ proxying for missing properties.
        """
        return {
            "id": self.id,
            "category": getattr(self._manifest_obj, "category", "system"),
            "name": self.name,
            "description": getattr(self._manifest_obj, "description", ""),
            "enabled": True,
            "permissions": getattr(self._manifest_obj, "permissions", []) or [],
            "active_in_group": False,
            "config_schema": None,
            "current_value": "",
            "config": {},
            "group_id": getattr(self._manifest_obj, "group_id", None),
            "group_exclusive": getattr(self._manifest_obj, "group_exclusive", True),
            "func_tag": self._manifest_obj.tags[0] if getattr(self._manifest_obj, "tags", None) else "Proxy",
            "llm_routes": []
        }

    async def initialize(self, context):
        self.context = context
        logger.info(f"🚀 Spawning Isolated Process for {self.id}...")
        
        self.process = multiprocessing.Process(
            target=host_entrypoint,
            args=(self._manifest_data, self.ipc_queue, self.event_queue),
            name=f"Plugin-{self.id}"
        )
        self.process.start()
        
        # Start Event Listener Loop
        asyncio.create_task(self._event_loop())
        
        # Send Init Command with Config Snapshot
        # Prepare Config Snapshot
        config = {}
        # SKIP CONFIG DUMP FOR NOW (MVP) - It hangs/crashes
        logger.info("Proxy: Skipping Config Snapshot (MVP)")
                 
        data_dir = ""
        if context and hasattr(context, 'get_data_dir'):
             data_dir = str(context.get_data_dir(self.id) or "") # Ensure string
        
        # [Phase 2] Pre-load plugin data to avoid sync RPC issues
        initial_data = {}
        if context and hasattr(context, 'load_data'):
            try:
                initial_data = context.load_data(self.id) or {}
                logger.info(f"Proxy: Pre-loaded {len(initial_data)} keys for {self.id}")
            except Exception as e:
                logger.warning(f"Proxy: Failed to pre-load data: {e}")
             
        req_id = str(uuid.uuid4())
        logger.info("Proxy: Putting to IPC Queue...")
        self.ipc_queue.put({
            "cmd": "initialize", 
            "id": "init_0", 
            "config": config,
            "data_dir": data_dir,
            "initial_data": initial_data  # [Phase 2] Include pre-loaded data
        })
        logger.info(f"➡️ Sent 'initialize' command to {self.id}")
        
        # Wait for Ack (with timeout)
        # For MVP, we presume success or catch failure in loop
        logger.info(f"✅ Isolated Process Started: PID {self.process.pid}")

    async def _event_loop(self):
        """Polls for events from child process"""
        while self.process and self.process.is_alive():
            try:
                # Non-blocking check or thread pool?
                # Using run_in_executor to avoid blocking main loop
                try:
                    msg = await asyncio.get_event_loop().run_in_executor(
                        None, self.event_queue.get, True, 0.1
                    )
                except:
                    # Empty
                    continue
                
                if msg["type"] == "emit":
                    # Re-emit on local bus
                    evt = msg.get("event")
                    logger.info(f"DEBUG: Proxy received emit: {evt.get('type')}")
                    
                    if self.context and self.context.bus:
                        # [RPC Router Bridge]
                        # If child is registering a route, the 'handler' is a useless pickled function (or None).
                        # We must replace it with an RPC Stub.
                        if evt.get("type") == "core.register_route_def":
                            payload = evt.get("payload", {})
                            handler_name = payload.get("handler_name")
                            
                            if handler_name:
                                # Define RPC Proxy Wrapper
                                # Define RPC Proxy Wrapper
                                from fastapi import Request
                                async def rpc_route_wrapper(request: Request):
                                    # Extract params from Request (Generic Proxy)
                                    kwargs = dict(request.query_params)
                                    # Attempt body parse
                                    try:
                                        body = await request.json()
                                        if isinstance(body, dict):
                                            kwargs.update(body)
                                    except:
                                        pass
                                        
                                    result = await self._rpc_call(handler_name, **kwargs)
                                    # [PR-4] Auto-Wrap RPC Streams
                                    # RPCStream is globally defined in this file
                                    if isinstance(result, RPCStream):
                                        from starlette.responses import StreamingResponse
                                        return StreamingResponse(result, media_type="text/event-stream")
                                    return result
                                
                                # Update payload with valid local handler
                                payload["handler"] = rpc_route_wrapper
                                logger.info(f"🔗 RPC Route Proxy created for {self.id}:{handler_name}")
                        
                        # FIXED: Unpack event dictionary for EventBus.emit()
                        # EventBus.emit(event_type: str, data: Any)
                        await self.context.bus.emit(evt["type"], evt.get("payload"))
                
                elif msg["type"] == "subscribe":
                    # [Phase 1] Child process registering event subscription
                    topic = msg.get("topic")
                    if topic and topic not in self._child_subscriptions:
                        self._child_subscriptions.add(topic)
                        # Subscribe to main EventBus and forward to child
                        async def forward_handler(event, t=topic):
                            await self._forward_event_to_child(t, event)
                        self.context.bus.subscribe(topic, forward_handler)
                        logger.info(f"📡 Forwarding '{topic}' events to child process {self.id}")

                elif msg["type"] == "sys.register":
                    # Proxy Registration
                    # The child process wants to register a service.
                    # We register THIS PROXY object as the service in the main process.
                    service_name = msg.get("name")
                    if self.context:
                        logger.info(f"🔗 Tunneling Service Registration: '{service_name}' -> Proxy({self.id})")
                        self.context.register_service(service_name, self)

                elif msg["type"] == "log":
                    # [PR-3] Bridge Child Log -> Main Logger
                    rec = msg.get("record", {})
                    lvl = rec.get("levelno", logging.INFO)
                    msg_text = rec.get("msg", "")
                    # Enrich with Child ID
                    child_logger = logging.getLogger(f"Child.{self.id}")
                    child_logger.log(lvl, f"{msg_text}")
                        
                elif msg["type"] == "result":
                    # Handle RPC results
                    req_id = msg.get("id")
                    if req_id in self._pending_requests:
                        future = self._pending_requests.pop(req_id)
                        if msg.get("status") == "ok":
                            future.set_result(msg.get("result")) 
                        else:
                            future.set_exception(Exception(msg.get("error")))
                
                # [PR-4] Streaming RPC Handlers
                elif msg["type"] == "stream_start":
                    req_id = msg.get("id")
                    if req_id in self._pending_requests:
                        future = self._pending_requests.pop(req_id)
                        # Create Stream Object
                        stream = RPCStream()
                        self._active_streams[req_id] = stream
                        # Resolve Future with the Stream Iterator
                        future.set_result(stream)
                        
                elif msg["type"] == "stream_chunk":
                    req_id = msg.get("id")
                    if req_id in self._active_streams:
                        chunk = msg.get("chunk")
                        self._active_streams[req_id].push(chunk)
                        
                elif msg["type"] == "stream_end":
                    req_id = msg.get("id")
                    if req_id in self._active_streams:
                        stream = self._active_streams.pop(req_id)
                        stream.close()
                    
            except Exception as e:
                import traceback
                logger.error(f"Error in RemoteProxy Event Loop: {e}\n{traceback.format_exc()}")
                pass # Queue empty or error
            
            await asyncio.sleep(0.01) # Faster polling for RPC

    def terminate(self):
        logger.info(f"🛑 Terminating Isolated Plugin {self.id}")
        if self.process:
            self.ipc_queue.put({"cmd": "teardown"})
            time.sleep(1) # Give it a grace period
            if self.process.is_alive():
                self.process.terminate()
            self.process.join()

    def __getattr__(self, name):
        """Forward unknown methods to child? (RPC)"""
        # For specific methods known to be called by Manager, we might need explicit stubs.
        # But for arbitrary calls, we can try generic proxying.
        return lambda *args, **kwargs: self._rpc_call(name, *args, **kwargs)

    async def _rpc_call(self, method, *args, **kwargs):
        req_id = str(uuid.uuid4())
        
        # Create Future
        loop = asyncio.get_running_loop()
        future = loop.create_future()
        self._pending_requests[req_id] = future
        
        self.ipc_queue.put({
            "cmd": "call",
            "id": req_id,
            "method": method,
            "args": args,
            "kwargs": kwargs
        })
        
        # Wait for result (with timeout)
        try:
            return await asyncio.wait_for(future, timeout=10.0)
        except asyncio.TimeoutError:
            self._pending_requests.pop(req_id, None)
            raise TimeoutError(f"RPC Call {method} timed out.")

    async def _forward_event_to_child(self, topic: str, event):
        """[Phase 1] Forward main process events to child via IPC"""
        try:
            event_data = event.dict() if hasattr(event, 'dict') else {"type": topic, "data": event}
            self.ipc_queue.put({
                "cmd": "event",
                "topic": topic,
                "event": event_data
            })
        except Exception as e:
            logger.warning(f"Failed to forward event '{topic}' to child: {e}")

