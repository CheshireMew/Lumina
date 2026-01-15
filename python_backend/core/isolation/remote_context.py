import logging
from typing import Any, Dict, Optional, List
from core.api.context import LuminaContext
from core.isolation.protocol import EventType, PluginEvent, EventEmitPayload

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
        self.event_queue.put(evt)

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
        Register a local handler for an event coming from Host.
        The Worker loop handles dispatching incoming events to these handlers.
        """
        # This registration happens in the worker's internal dispatcher, 
        # not sent to Host immediately (Host knows subscriptions via manifest? 
        # Or we need to send a 'subscribe' command?)
        # For V1, let's assume Host blindly forwards subscribed events 
        # based on Manifest, OR we send a dynamic subscription message.
        pass

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
        # TODO: This requires synchronous Request-Reply logic which is complex in Queues.
        # Strategy: Pass initial data in 'start' command. 
        # Runtime load_data might be cached or unimplemented for V1.
        logger.warning("RemoteContext.load_data only returns cached config")
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
