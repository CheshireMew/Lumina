import logging
import threading
import multiprocessing
import traceback
from typing import Dict, Any, Optional

from core.isolation.protocol import PluginCommand, CommandType, EventType, LoadPayload, PluginEvent
from services.plugin_worker import run_worker
from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger("RemotePluginProxy")

class RemotePluginProxy(BaseSystemPlugin):
    """
    A proxy that masquerades as a System Plugin but runs the actual logic
    in a separate child process.
    """

    def __init__(self, manifest: Dict[str, Any], manifest_path: str):
        self._manifest = manifest
        self._manifest_path = manifest_path
        self._process: Optional[multiprocessing.Process] = None
        self._cmd_queue: Optional[multiprocessing.Queue] = None
        self._event_queue: Optional[multiprocessing.Queue] = None
        self._listener_thread: Optional[threading.Thread] = None
        self._stop_event = threading.Event()
        self._config_cache = {}

    @property
    def id(self) -> str:
        return self._manifest.get("id")

    @property
    def name(self) -> str:
        return self._manifest.get("name", "Unknown Remote Plugin")
    
    @property
    def description(self) -> str:
        return self._manifest.get("description", "")

    @property
    def config_schema(self) -> Optional[Dict]:
        return self._manifest.get("config_schema")

    @property
    def category(self) -> str:
        return self._manifest.get("category", "system")

    # Override config property to use local cache + async update
    @property
    def config(self) -> dict:
        return self._config_cache

    def update_config(self, key: str, value: Any):
        self._config_cache[key] = value
        # Send update to worker
        # TODO: Implement UPDATE_CONFIG command in Worker
        pass

    def initialize(self, context: Any):
        self.context = context
        # Initial config load
        self._config_cache = self.load_data() or {}

        logger.info(f"馃殌 Spawning Isolated Process for {self.id}...")
        
        # 1. Setup Queues
        self._cmd_queue = multiprocessing.Queue()
        self._event_queue = multiprocessing.Queue()
        
        # 2. Spawn Process
        # Use 'spawn' for Windows compatibility/safety
        ctx = multiprocessing.get_context('spawn')
        self._process = ctx.Process(
            target=run_worker,
            args=(self._cmd_queue, self._event_queue),
            name=f"PluginWorker-{self.id}",
            daemon=True 
        )
        self._process.start()
        
        # 3. Start Listener Thread
        self._listener_thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._listener_thread.start()
        
        # 4. Send LOAD Command
        cmd = PluginCommand(
            id=self.id,
            type=CommandType.LOAD,
            payload=LoadPayload(
                plugin_id=self.id,
                manifest_path=str(self._manifest_path),
                config=self._config_cache,
                permissions=self._manifest.get("permissions", [])
            ).dict()
        )
        self._cmd_queue.put(cmd.dict())
        
    def terminate(self):
        logger.info(f"Terminating Remote Plugin {self.id}")
        self._stop_event.set()
        if self._cmd_queue:
            self._cmd_queue.put(PluginCommand(id=self.id, type=CommandType.TERMINATE).dict())
        
        if self._process:
            self._process.join(timeout=2.0)
            if self._process.is_alive():
                self._process.terminate()

    def _listen_loop(self):
        """Background thread to drain event queue from worker"""
        logger.debug(f"[{self.id}] Listener thread started")
        while not self._stop_event.is_set():
            try:
                if not self._process or not self._process.is_alive():
                    logger.error(f"[{self.id}] Process died unexpectedly!")
                    break
                
                # Get with timeout to check stop_event
                try:
                    raw_evt = self._event_queue.get(timeout=1.0)
                except: # Empty
                    continue
                
                evt = PluginEvent(**raw_evt)
                
                if evt.type == EventType.LOG:
                    lvl = evt.payload.get("level", "info")
                    msg = f"[{self.id}] {evt.payload.get('message')}"
                    if lvl == "error": logger.error(msg)
                    elif lvl == "warning": logger.warning(msg)
                    else: logger.info(msg)
                    
                elif evt.type == EventType.EVENT_EMIT:
                    # Proxy Event emission
                    name = evt.payload.get("event_name")
                    data = evt.payload.get("data")
                    if self.context and name:
                        self.context.bus.emit(name, data)
                        
                elif evt.type == EventType.ERROR:
                    logger.error(f"[{self.id}] REMOTE ERROR: {evt.payload.get('message')}\n{evt.payload.get('traceback')}")

                elif evt.type == EventType.SAVE_DATA:
                    # Worker requested persistence
                    key = evt.payload.get("key")
                    data = evt.payload.get("data")
                    self.save_data(data) # BaseSystemPlugin.save_data handles id-scoping. Key usage?
                    # BaseSystemPlugin.save_data(data) saves to {id}.json
                    # If key is provided and distinct from defaults, we might need a custom path?
                    # For now, V1 convention: save_data(data) -> overwrites plugin's data file.
                    # Ignore 'key' unless we implement KV store.
                    
                elif evt.type == EventType.UPDATE_CONFIG:
                    # Worker requested config update
                    key = evt.payload.get("key")
                    val = evt.payload.get("value")
                    if key:
                        self.update_config(key, val)
                    
            except Exception as e:
                logger.error(f"[{self.id}] Listener Error: {e}")
                
        logger.debug(f"[{self.id}] Listener thread stopped")
