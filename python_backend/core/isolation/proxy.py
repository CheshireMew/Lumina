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
    def __init__(self, event_queue):
        self.bus = self
        self._queue = event_queue

    async def emit(self, event):
        # Flatten event to dict if needed
        payload = event.dict() if hasattr(event, 'dict') else event
        self._queue.put({"type": "emit", "event": payload})

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

class RemotePluginProxy(BaseSystemPlugin):
    """
    Proxies calls to a child process via multiprocessing.Queue.
    """
    def __init__(self, manifest_data: dict):
        self._manifest_data = manifest_data
        self._manifest_obj = PluginManifest(**manifest_data)
        
        self.ipc_queue = multiprocessing.Queue()
        self.event_queue = multiprocessing.Queue()
        self.process: Optional[multiprocessing.Process] = None
        self.context = None # Parent context
        
        # RPC Futures: request_id -> Future
        # RPC Futures: request_id -> Future
        self._pending_requests: Dict[str, asyncio.Future] = {}
        
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
        Remote plugins must sync schema via IPC.
        For now, prevent crash by returning None instead of __getattr__ proxy.
        TODO: Sync schema during initialization.
        """
        return None 

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
        config_snapshot = {}
        if hasattr(context, 'config'):
            # Dump Pydantic settings to dict
            # app_settings is commonly a Pydantic BaseSettings
            try:
                config_snapshot = context.config.model_dump() 
            except:
                config_snapshot = vars(context.config) if hasattr(context.config, '__dict__') else {}

        # Resolve Data Dir
        data_dir = ""
        if hasattr(context, 'get_data_dir'):
             data_dir = str(context.get_data_dir(self.id))
        
        req_id = str(uuid.uuid4())
        self.ipc_queue.put({
            "cmd": "initialize", 
            "id": req_id, 
            "config": config_snapshot,
            "data_dir": data_dir
        })
        
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
                    # Reconstruct if needed, or pass raw dict if bus supports it
                    # Assuming bus.emit accepts dicts or converting
                    if self.context and self.context.bus:
                        # TODO: Convert dict back to EventPacket? 
                        # For now, MVP assumes loose typing
                        await self.context.bus.emit(evt)

                elif msg["type"] == "sys.register":
                    # Proxy Registration
                    # The child process wants to register a service.
                    # We register THIS PROXY object as the service in the main process.
                    service_name = msg.get("name")
                    if self.context:
                        logger.info(f"🔗 Tunneling Service Registration: '{service_name}' -> Proxy({self.id})")
                        self.context.register_service(service_name, self)
                        
                elif msg["type"] == "result":
                    # Handle RPC results
                    req_id = msg.get("id")
                    if req_id in self._pending_requests:
                        future = self._pending_requests.pop(req_id)
                        if msg.get("status") == "ok":
                            future.set_result(msg.get("result")) 
                        else:
                            future.set_exception(Exception(msg.get("error")))
                    
            except Exception as e:
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
