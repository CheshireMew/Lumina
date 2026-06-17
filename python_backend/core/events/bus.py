"""
Lumina EventBus - Core Event System for Plugin Architecture
Pub/Sub Event-Driven Plugin Communication

Features:
- Async event subscription and publishing
- Wildcard subscriptions (e.g., "system.*")
- Runtime plugin loading/unloading support
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Type
from dataclasses import dataclass, field
from collections import defaultdict
import fnmatch
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("EventBus")


def _safe_timestamp():
    import time
    try:
        loop = asyncio.get_running_loop()
        return loop.time()
    except RuntimeError:
        return time.time()

@dataclass
class Event:
    """Standard Event Payload"""
    type: str
    data: Any = None
    source: str = "system"
    timestamp: float = field(default_factory=_safe_timestamp)

@dataclass
class EventSchema:
    """Schema definition for an event type (Phase 30)"""
    version: str
    payload_model: Type[BaseModel]
    description: str = ""


class EventBus:
    """
    Central Event Bus for Lumina.
    
    Usage:
        # Subscribe to events
        bus.subscribe("system.tick", my_handler)
        bus.subscribe("plugin.*", wildcard_handler)
        
        # Register Schema (Optional but recommended)
        class MyPayload(BaseModel):
            status: str
        bus.register_schema("my_plugin.status", EventSchema("1.0", MyPayload))
        
        # Publish events
        await bus.emit("my_plugin.status", {"status": "ok"})
    """
    
    def __init__(self):
        # Event subscriptions: event_type -> list of callbacks
        self._subscriptions: Dict[str, List[Callable]] = defaultdict(list)
        # Wildcard subscriptions
        self._wildcard_subscriptions: List[tuple] = []  # (pattern, callback)
        # Event Schemas
        self._schemas: Dict[str, EventSchema] = {}
        # Track subscription IDs for unsubscribe
        self._sub_id = 0
        self._sub_map: Dict[int, tuple] = {}  # id -> (event_type, callback)
        
    def register_schema(self, event_type: str, schema: EventSchema):
        """Register a schema for an event type."""
        self._schemas[event_type] = schema
        logger.debug(f"馃摑 Registered schema for '{event_type}' (v{schema.version})")

    def subscribe(self, event_type: str, callback: Callable) -> int:
        """
        Subscribe to an event type.
        
        Args:
            event_type: Event type string (e.g., "system.tick", "plugin.*")
            callback: Async or sync function to call when event fires
            
        Returns:
            Subscription ID (use for unsubscribe)
        """
        self._sub_id += 1
        sub_id = self._sub_id
        
        if "*" in event_type:
            self._wildcard_subscriptions.append((event_type, callback))
            self._sub_map[sub_id] = ("__wildcard__", (event_type, callback))
        else:
            self._subscriptions[event_type].append(callback)
            self._sub_map[sub_id] = (event_type, callback)
        
        logger.debug(f"馃摗 Subscribed to '{event_type}' (ID: {sub_id})")
        return sub_id
    
    def unsubscribe(self, sub_id: int) -> bool:
        """Unsubscribe using subscription ID."""
        if sub_id not in self._sub_map:
            return False
        
        event_type, callback = self._sub_map[sub_id]
        
        if event_type == "__wildcard__":
            pattern, cb = callback
            self._wildcard_subscriptions = [
                (p, c) for p, c in self._wildcard_subscriptions 
                if not (p == pattern and c == cb)
            ]
        else:
            if callback in self._subscriptions[event_type]:
                self._subscriptions[event_type].remove(callback)
        
        del self._sub_map[sub_id]
        logger.debug(f"馃摗 Unsubscribed ID: {sub_id}")
        return True
    
    async def emit(self, event_type: str, data: Any = None, source: str = "system") -> int:
        """
        Emit an event to all subscribers.
        Validates payload if schema is registered.
        """
        # Schema Validation
        if event_type in self._schemas:
            schema = self._schemas[event_type]
            payload = data
            
            from core.protocol import EventPacket
            if isinstance(data, EventPacket):
                payload = data.payload

            try:
                # Validate payload against Pydantic model
                if payload is None:
                    # Treat None as empty dict for validation validation
                    schema.payload_model(**{})
                elif isinstance(payload, BaseModel):
                    # If it's already a model, re-validate it against the event schema.
                    if not isinstance(payload, schema.payload_model):
                        schema.payload_model(**payload.dict())
                else: 
                    # Dict or other (assume dict-like)
                    if isinstance(payload, dict):
                        schema.payload_model(**payload)
                    else:
                        raise ValueError(f"Invalid payload type: {type(payload)}")
            except ValidationError as ve:
                logger.error(f"❌ Event Validation Failed for '{event_type}': {ve}")
                # [Hardening] Log the faulty data for easier debugging
                logger.debug(f"Faulty Data: {payload}")
                return 0
            except Exception as e:
                logger.error(f"❌ Schema Validation Error for '{event_type}': {e}")
                return 0

        event = Event(type=event_type, data=data, source=source)
        handlers_called = 0
        
        # Direct subscriptions
        for callback in self._subscriptions.get(event_type, []):
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(event)
                else:
                    callback(event)
                handlers_called += 1
            except Exception as e:
                logger.error(f"Event handler error for '{event_type}': {e}")
        
        # Wildcard subscriptions
        for pattern, callback in self._wildcard_subscriptions:
            if fnmatch.fnmatch(event_type, pattern):
                try:
                    if asyncio.iscoroutinefunction(callback):
                        await callback(event)
                    else:
                        callback(event)
                    handlers_called += 1
                except Exception as e:
                    logger.error(f"Wildcard handler error for '{pattern}' on '{event_type}': {e}")
        
        if handlers_called > 0:
            # [DEBUG] Log handler count for BRAIN_RESPONSE to check for duplicates
            if event_type == "brain_response":
                logger.info(f"🔔 Emitted '{event_type}' to {handlers_called} handlers")
            else:
                logger.debug(f"Emitted '{event_type}' to {handlers_called} handlers")
        
        return handlers_called
    
    async def wait_for(self, event_type: str, predicate: Callable[[Event], bool] = None, timeout: float = 5.0) -> Optional[Event]:
        """
        Wait for a specific event.
        
        Args:
            event_type: Event type to wait for.
            predicate: Optional function(event) -> bool. Return True to accept event.
            timeout: Max seconds to wait.
            
        Returns:
            Event object if found, None if timeout.
        """
        future = asyncio.get_running_loop().create_future()
        
        def _callback(event: Event):
            if not future.done():
                try:
                    if predicate is None or predicate(event):
                        future.set_result(event)
                except Exception as e:
                    logger.error(f"wait_for predicate failed: {e}")
        
        sub_id = self.subscribe(event_type, _callback)
        try:
            return await asyncio.wait_for(future, timeout=timeout)
        except asyncio.TimeoutError:
            return None
        finally:
            self.unsubscribe(sub_id)

    def emit_sync(self, event_type: str, data: Any = None, source: str = "system"):
        """
        Synchronous emit for non-async contexts.
        Creates a new event loop if needed.
        """
        try:
            asyncio.get_running_loop()
            asyncio.create_task(self.emit(event_type, data, source))
        except RuntimeError:
            # No running loop
            asyncio.run(self.emit(event_type, data, source))
    
    # --- Capability Module Lifecycle Events ---
    
    async def capability_module_loaded(self, module_id: str, module_instance: Any):
        """Emit capability module loaded event."""
        await self.emit("capability.loaded", {"id": module_id, "instance": module_instance})
    
    async def capability_module_unloaded(self, module_id: str):
        """Emit capability module unloaded event."""
        await self.emit("capability.unloaded", {"id": module_id})

    def bulk_register_schemas(self, schemas: Dict[str, Type[BaseModel]], version: str = "1.0"):
        """Bulk register schemas for multiple event types."""
        for event_type, model in schemas.items():
            self.register_schema(event_type, EventSchema(version=version, payload_model=model))
        logger.info(f"⚡ Bulk Registered {len(schemas)} Event Schemas")

    # --- Utilities ---
    
    def throttle(self, event_type: str, interval: float = 1.0):
        """
        Decorator/Helper to throttle event emission.
        Usage:
            @bus.throttle("status.update", 0.5)
            async def send_status(data): ...
        """
        # Limiter logic implementation requires state tracking per event/source.
        # Simple implementation: Return a wrapper that checks last emit time.
        last_emit = {}
        
        def decorator(func):
            async def wrapper(*args, **kwargs):
                import time
                now = time.time()
                if now - last_emit.get(event_type, 0) >= interval:
                    last_emit[event_type] = now
                    return await func(*args, **kwargs)
        return decorator

    # --- Monitoring & Stats ---
    
    # Warning thresholds for potential leaks
    SUBSCRIPTION_WARN_THRESHOLD = 100  # Warn if single event has > 100 subscribers
    TOTAL_SUBSCRIPTION_WARN = 500      # Warn if total subscriptions > 500
    
    def get_stats(self) -> dict:
        """
        Get EventBus statistics for monitoring.
        
        Returns:
            {
                "total_subscriptions": int,
                "event_types": int,
                "wildcard_subscriptions": int,
                "schemas": int,
                "top_events": [(event_type, count), ...]
            }
        """
        # Count subscriptions per event
        event_counts = {
            event: len(callbacks) 
            for event, callbacks in self._subscriptions.items()
        }
        
        # Sort by count descending
        top_events = sorted(event_counts.items(), key=lambda x: -x[1])[:10]
        
        return {
            "total_subscriptions": sum(len(cbs) for cbs in self._subscriptions.values()),
            "event_types": len(self._subscriptions),
            "wildcard_subscriptions": len(self._wildcard_subscriptions),
            "schemas": len(self._schemas),
            "top_events": top_events,
        }
    
    def check_for_leaks(self) -> list:
        """
        Check for potential subscription leaks.
        
        Returns:
            List of warning messages, empty if no leaks detected
        """
        warnings = []
        stats = self.get_stats()
        
        # Check total
        if stats["total_subscriptions"] > self.TOTAL_SUBSCRIPTION_WARN:
            warnings.append(
                f"⚠️ High subscription count: {stats['total_subscriptions']} "
                f"(threshold: {self.TOTAL_SUBSCRIPTION_WARN})"
            )
        
        # Check per-event
        for event_type, count in stats["top_events"]:
            if count > self.SUBSCRIPTION_WARN_THRESHOLD:
                warnings.append(
                    f"⚠️ Possible leak on '{event_type}': {count} subscribers "
                    f"(threshold: {self.SUBSCRIPTION_WARN_THRESHOLD})"
                )
        
        return warnings
    
    def log_stats(self):
        """Log current EventBus statistics."""
        stats = self.get_stats()
        logger.info(
            f"📊 EventBus Stats: "
            f"{stats['total_subscriptions']} subs, "
            f"{stats['event_types']} events, "
            f"{stats['schemas']} schemas"
        )
        
        # Check for leaks
        warnings = self.check_for_leaks()
        for w in warnings:
            logger.warning(w)


# Global singleton (initialized in main.py)
_bus_instance: Optional[EventBus] = None


def get_event_bus() -> EventBus:
    """Get the global EventBus instance."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
    return _bus_instance


def init_event_bus() -> EventBus:
    """Initialize and return the global EventBus."""
    global _bus_instance
    if _bus_instance is None:
        _bus_instance = EventBus()
        logger.info("⚡ EventBus Initialized")
    return _bus_instance

# Export Singleton
bus = get_event_bus()
