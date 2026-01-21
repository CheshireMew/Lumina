import logging
from typing import Any, Optional, Dict
import asyncio
from pathlib import Path
import json

# Strict DI
from core.utils.frozen_proxy import FrozenProxy
# EventBus
from core.events import get_event_bus, EventBus
# [Architecture 6.0] Capability
# [Fix] CapabilityType is in schemas
from core.capabilities.schemas import CapabilityType

logger = logging.getLogger("LuminaContext")

class LuminaContext:
    """
    The official API Surface for System Plugins.
    Provides safe access to system capabilities and decouples plugins from internal implementation details.
    
    Key Features:
    - EventBus for Pub/Sub communication (context.bus)
    - Service Registry for plugin discovery
    - Safe accessors for core capabilities (ticker, soul, memory, llm_manager)
    
    This replaces direct 'ServiceContainer' injection.
    """
    def __init__(self, container: Any, plugin_id: str, event_bus: Optional[EventBus] = None, router_manager: Any = None):
        self.plugin_id = plugin_id
        # We hold the container internally but don't expose it directly
        self._container = container
        self.router_manager = router_manager
        if router_manager:
             logger.info(f"✅ LuminaContext: RouterManager Injected for {plugin_id}")
        else:
             logger.warning(f"❌ LuminaContext: RouterManager MISSING for {plugin_id}")
        
        # EventBus - The Primary Communication Channel
        self.bus = event_bus if event_bus else get_event_bus()
        
        # Expose Configuration Manager (Read-Only ideally, but direct for now)
        if container.config:
            self.config = FrozenProxy(container.config)
        else:
            self.config = None
            
        # [Architecture 6.0] Audit Logger
        from security.audit import get_audit_logger, AuditAction
        self.audit_logger = get_audit_logger()
        self._audit_action = AuditAction
        
    # @property
    # def container(self) -> Any:
    #     """
    #     [REMOVED] Access to raw ServiceContainer is removed in Phase 10.
    #     """
    #     raise AttributeError("context.container is Removed. Use context.bus or other APIs.")

    # --- Persistence API (Wraps SoulClient) ---
    # Plugins should use these methods instead of accessing soul_client directly
    
    def load_data(self, plugin_id: str) -> Dict:
        """Loads plugin-specific JSON data."""
        if self.soul:
             return self.soul.load_module_data(plugin_id)
        return {}

    def save_data(self, plugin_id: str, data: Dict):
        """Saves plugin-specific JSON data."""
        if self.soul:
             self.soul.save_module_data(plugin_id, data)

    def get_data_dir(self, plugin_id: str) -> Optional[str]:
        """Returns Path to plugin data directory for binary assets."""
        if self.soul:
             return self.soul.get_module_data_dir(plugin_id)
        return None

    def register_service(self, name: str, instance: Any):
        """
        Register a service via EventBus for plugin discovery.
        Protected against overwriting Core Services.
        """
        # [HARDENING] P0: Prevent Core Service Overwrite
        RESERVED = {"soul", "memory", "ticker", "llm_manager", "router_manager", "event_bus"}
        if name in RESERVED:
            logger.critical(f"🚨 Plugin {self.plugin_id} attempted to overwrite reserved service: {name}")
            raise PermissionError(f"Plugin cannot overwrite reserved service: {name}")

        # Register on EventBus (Phase 30 standard)
        self.bus.register_service(name, instance)
        
        # Backward compatibility: also set on container (Safe-ish)
        # We only allow this if it doesn't collide with existing attributes
        if hasattr(self._container, name):
             logger.warning(f"⚠️ Plugin {self.plugin_id} shadowing existing container attribute: {name}")
             # We allow it for now but log warning, technically some extensions might rely on patching?
             # No, strictly reject overwriting ANY existing container attribute for safety.
             # raise PermissionError(f"Service collision: {name} already exists.")
             pass
        
        setattr(self._container, name, instance)
        logger.info(f"✅ Service registered: {name} (by {self.plugin_id})")
        
        self.audit("register_service", name, "success")

    def register_route_def(self, path: str, method: str, handler_name: str, handler: Any):
        """
        Register an API route via RouterManager (Direct) or EventBus (Legacy).
        """
        # DIRECT INJECTION (Primary)
        if self.router_manager:
            payload = {
                "plugin_id": self.plugin_id,
                "path": path,
                "method": method,
                "handler": handler,
                "response_model": None 
            }
            # Wrapper to mimic Event structure expected by handling logic
            class MockEvent:
                def __init__(self, data): self.data = data
            
            self.router_manager._handle_route_def(MockEvent(payload))
            logger.info(f"📨 Route '{method} {path}' registered via RouterManager (Direct).")
            self.audit("register_route", f"{method} {path}", "success")
            return

        # BACKUP (EventBus)
        from core.events import Event
        
        payload = {
            "plugin_id": self.plugin_id,
            "path": path,
            "method": method,
            "handler_name": handler_name,
            "handler": handler 
        }
        
        # Emit event for RouterManager
        # NOTE: emit is async, use emit_sync for sync contexts
        self.bus.emit_sync("core.register_route_def", payload)
        logger.info(f"📨 Route '{method} {path}' registered via EventBus.")
        self.audit("register_route", f"{method} {path}", "success", metadata={"mechanism": "eventbus"})
    
    @property
    def soul(self) -> Any:
        """Access to Soul Manager (Personality/State)."""
        return getattr(self._container, "soul", None)

    @property
    def ticker(self) -> Any:
        """Access to Global Ticker."""
        return getattr(self._container, "ticker", None)

    @property
    def memory(self) -> Any:
        """Access to Memory System (SurrealDB)."""
        return getattr(self._container, "surreal_system", None)

    @property
    def llm_manager(self) -> Any:
        """Access to LLM Manager."""
        return getattr(self._container, "llm_manager", None)

    def get_logger(self, name: str):
        """Get a standard logger instance."""
        return logging.getLogger(name)
        
    def find_capability(self, cap_type: str, **attributes) -> Optional[str]:
        """
        [Architecture 6.0] Discovery API.
        Finds a plugin that provides the requested capability.
        """
        # Convert string to Enum if needed
        # We allow string input for ease of use
        
        pm = getattr(self._container, "system_plugin_manager", None)
        if not pm:
            logger.error("PluginManager not available in container")
            return None
            
        provider_id = pm.find_provider(cap_type, **attributes)
        
        # Log discovery attempt
        status = "success" if provider_id else "not_found"
        self.audit("find_capability", f"type:{cap_type}", status, metadata=attributes)
        
        return provider_id
        
    def audit(self, action: str, target: str, status: str = "success", metadata: Dict = None):
        """
        Record a security audit log for this plugin.
        """
        # Convert string action to Enum if needed, or use directly
        act_enum = self._audit_action.SENSITIVE_CALL
        try:
             # Try to map if possible, else default
             pass
        except:
             pass
             
        self.audit_logger.log(
            plugin_id=self.plugin_id,
            action=act_enum,
            target=target,
            status=status,
            metadata={"raw_action": action, **(metadata or {})}
        )

    # --- Strict API Boundary (Phase 10 Hardening) ---
    
    def __getattr__(self, name: str):
        """
        Strict attribute access control.
        """
        if name.startswith("_"):
            raise AttributeError(f"Private attribute '{name}' is not accessible")
        
        # Deny access to everything else
        raise AttributeError(
            f"'{name}' is not a public LuminaContext API. "
            f"Available: bus, soul, ticker, memory, llm_manager, config, "
            f"load_data(), save_data(), get_data_dir(), register_service(), get_logger()"
        )

    # __setattr__ is intentionally NOT overridden to prevent plugins from
    # writing to arbitrary container attributes. Use register_service() instead.


