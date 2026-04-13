import time
import logging
from typing import Dict, Any, Callable, List
from threading import RLock

logger = logging.getLogger("Automation.Context")

class StateStore:
    """
    In-Memory Key-Value Store for System State.
    Supports TTL and Change Listeners.
    """
    def __init__(self):
        self._store: Dict[str, Any] = {}
        self._metadata: Dict[str, Dict] = {} # e.g. timestamp, ttl
        self._listeners: List[Callable[[str, Any, Any], None]] = []
        self._lock = RLock()

    def set(self, key: str, value: Any, ttl: float = 0):
        """
        Update state. Triggers listeners if changed.
        """
        with self._lock:
            old_value = self._store.get(key)
            
            # Simple equality check to avoid noise
            if old_value == value:
                # Update timestamp even if value same? 
                # Ideally yes for "heartbeat" style checks, but trigger logic might differ.
                self._update_metadata(key, ttl)
                return

            self._store[key] = value
            self._update_metadata(key, ttl)
        
        # Notify Listeners (outside lock to prevent deadlocks in callbacks)
        self._notify_listeners(key, old_value, value)

    def get(self, key: str, default: Any = None) -> Any:
        with self._lock:
            self._cleanup_expired(key)
            return self._store.get(key, default)

    def get_all(self) -> Dict[str, Any]:
        """Snapshot of current state"""
        with self._lock:
            # Cleanup all potentially expired? Or lazy?
            # Lazy for perf, but snapshot might need accuracy.
            keys = list(self._store.keys())
            for k in keys: self._cleanup_expired(k)
            return dict(self._store)

    def subscribe(self, callback: Callable[[str, Any, Any], None]):
        """Callback signature: (key, old_value, new_value)"""
        self._listeners.append(callback)

    def _update_metadata(self, key: str, ttl: float):
        now = time.time()
        meta = {
            "updated_at": now,
            "expiry": (now + ttl) if ttl > 0 else None
        }
        self._metadata[key] = meta

    def _cleanup_expired(self, key: str):
        meta = self._metadata.get(key)
        if not meta: return
        
        expiry = meta.get("expiry")
        if expiry and time.time() > expiry:
            logger.debug(f"State expired: {key}")
            del self._store[key]
            del self._metadata[key]
            # Notify deletion? (new_value = None)
            # For now, silent cleanup to avoid triggers on expiration?
            # Or explicit expiry event? Silent is safer for V1.

    def _notify_listeners(self, key: str, old_val: Any, new_val: Any):
        for listener in self._listeners:
            try:
                listener(key, old_val, new_val)
            except Exception as e:
                logger.error(f"State listener error: {e}")
