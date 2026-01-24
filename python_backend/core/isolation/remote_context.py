import logging
from typing import Any, Dict
from core.api.context import LuminaContext
from core.isolation.protocol import EventType, PluginEvent

logger = logging.getLogger("RemoteContext")

class RemoteContext:
    """
    A context implementation for plugins running in a separate process.
    Proxies all core actions to the Host process via IPC.
    Does NOT inherit from LuminaContext directly to avoid dragging in heavy dependencies,
    but implements the same public API.
    """
    
    def __init__(self, plugin_id: str, event_queue: Any):
        self.plugin_id = plugin_id
        self.event_queue = event_queue
        self.config: Dict[str, Any] = {} # Synced config
        
        # Mock objects to satisfy plugin API
        self.bus = self
        
    def _send(self, event_type: EventType, payload: Dict[str, Any]):
        """Helper to push event to queue"""
        evt = PluginEvent(type=event_type, plugin_id=self.plugin_id, payload=payload)
        # Assuming event_queue is a multiprocessing.Queue
        # Serialize to dict to ensure compatibility with Proxy consumers logic
        self.event_queue.put(evt.dict())

    # --- EventBus Proxy ---

    def emit(self, event_name: str, data: Dict[str, Any] = None):
        """Proxy emit to host"""
        if data is None: data = {}
        payload = {"event_name": event_name, "data": data}
        self._send(EventType.EVENT_EMIT, payload)
        
    def emit_sync(self, event_name: str, data: Dict[str, Any] = None):
        """
        Proxy emit_sync. 
        NOTE: In async IPC, true 'sync' return is hard without blocking.
        For now, we treat it as fire-and-forget or async emit.
        Ideally isolated plugins should rely on async patterns.
        """
        self.emit(event_name, data)

    def subscribe(self, event_name: str, handler):
        """
        [Phase 1] Register a local handler for an event coming from Host.
        Sends subscription request to main process for forwarding.
        """
        if not hasattr(self, '_local_handlers'):
            self._local_handlers = {}
        
        self._local_handlers[event_name] = handler
        
        # Notify main process to forward this event type
        self.event_queue.put({
            "type": "subscribe",
            "topic": event_name
        })
        logger.debug(f"[RemoteContext] Subscribed to '{event_name}', forwarding request to main process")

    # --- Data Persistence Proxy ---

    def save_data(self, key: str, data: Dict):
        """
        Request Host to save data.
        Args:
            key: Unused in V1 interface (PluginID is implicit?), or typically "plugin_id"
            data: The JSON data to save.
        """
        # We ignore 'key' if it's meant to be plugin_id, as context is bound to plugin_id.
        # But if valid use case uses sub-keys, we might payload it.
        # Standard LuminaContext.save_data(id, data)...
        payload = {"key": key, "data": data}
        self._send(EventType.SAVE_DATA, payload)
        
    def update_config(self, key: str, value: Any):
        """Request Host to update config."""
        # Update local cache optimistically
        self.config[key] = value
        payload = {"key": key, "value": value}
        self._send(EventType.UPDATE_CONFIG, payload)

    def load_data(self, key: str) -> Dict:
        """
        [Phase 2] Returns pre-loaded data cache instead of empty dict.
        Data is passed during initialize from main process.
        """
        if hasattr(self, '_data_cache') and self._data_cache:
            return self._data_cache
        logger.debug("RemoteContext.load_data: No cached data available")
        return {}

    # --- Logging ---
    def log(self, level: str, message: str):
        payload = {"level": level, "message": message}
        self._send(EventType.LOG, payload)

class RemoteContextAdapter(LuminaContext):
    """
    If plugins doing strict type checks `isinstance(ctx, LuminaContext)`,
    we might need this inheritance. But for now, duck typing is preferred.
    """
    pass
