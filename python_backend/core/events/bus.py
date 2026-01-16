"""
Lumina EventBus - Core Event System for Plugin Architecture
Pub/Sub Event-Driven Plugin Communication

Features:
- Async event subscription and publishing
- Wildcard subscriptions (e.g., "system.*")
- Service registration via events
- Runtime plugin loading/unloading support
"""

import asyncio
import logging
from typing import Any, Callable, Dict, List, Optional, Set, Type
from dataclasses import dataclass, field
from collections import defaultdict
import fnmatch
from pydantic import BaseModel, ValidationError

logger = logging.getLogger("EventBus")


@dataclass
class Event:
    """Standard Event Payload"""
    type: str
    data: Any = None
    source: str = "system"
    timestamp: float = field(default_factory=lambda: asyncio.get_event_loop().time() if asyncio.get_event_loop().is_running() else 0)


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
        # Service registry
        self._services: Dict[str, Any] = {}
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
            try:
                # Validate data against Pydantic model
                if data is None:
                    # Allow None only if model allows optional fields?
                    # Dict can be empty.
                    pass 
                elif isinstance(data, dict):
                    # Validate dict matches model
                    schema.payload_model(**data)
                elif isinstance(data, BaseModel):
                    # Ensure it matches the expected model type or is compatible
                    if not isinstance(data, schema.payload_model):
                         # Try conversion?
                         schema.payload_model(**data.dict())
            except ValidationError as ve:
                logger.error(f"鉂?Event Validation Failed for '{event_type}': {ve}")
                return 0
            except Exception as e:
                logger.error(f"鉂?Schema Validation Error for '{event_type}': {e}")
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
            logger.debug(f"Emitted '{event_type}' to {handlers_called} handlers")
        
        return handlers_called
    
    def emit_sync(self, event_type: str, data: Any = None, source: str = "system"):
        """
        Synchronous emit for non-async contexts.
        Creates a new event loop if needed.
        """
        try:
            loop = asyncio.get_running_loop()
            asyncio.create_task(self.emit(event_type, data, source))
        except RuntimeError:
            # No running loop
            asyncio.run(self.emit(event_type, data, source))
    
    # --- Service Registry ---
    
    def register_service(self, name: str, instance: Any):
        """
        Register a service (plugin instance) to the bus.
        This allows other plugins to discover and use services.
        
        Args:
            name: Service identifier (e.g., "heartbeat", "voiceprint")
            instance: The service instance
        """
        self._services[name] = instance
        logger.info(f"馃攲 Service Registered: {name}")
        # Emit event for dynamic discovery
        self.emit_sync("service.registered", {"name": name, "instance": instance})
    
    def unregister_service(self, name: str) -> bool:
        """Unregister a service."""
        if name in self._services:
            del self._services[name]
            logger.info(f"馃攲 Service Unregistered: {name}")
            self.emit_sync("service.unregistered", {"name": name})
            return True
        return False
    
    def get_service(self, name: str) -> Optional[Any]:
        """Get a registered service by name."""
        return self._services.get(name)
    
    def list_services(self) -> List[str]:
        """List all registered service names."""
        return list(self._services.keys())
    
    # --- Plugin Lifecycle Events ---
    
    async def plugin_loaded(self, plugin_id: str, plugin_instance: Any):
        """Emit plugin loaded event."""
        await self.emit("plugin.loaded", {"id": plugin_id, "instance": plugin_instance})
    
    async def plugin_unloaded(self, plugin_id: str):
        """Emit plugin unloaded event."""
        await self.emit("plugin.unloaded", {"id": plugin_id})

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
            return wrapper
        return decorator


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
    _bus_instance = EventBus()
    logger.info("馃殞 EventBus Initialized")
    return _bus_instance
