import logging
from typing import Any, Optional, Dict
import asyncio
from pathlib import Path
import json

# Strict DI
from core.utils.frozen_proxy import FrozenProxy
# EventBus
from core.events import get_event_bus, EventBus

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
    def __init__(self, container: Any, event_bus: Optional[EventBus] = None):
        # We hold the container internally but don't expose it directly
        self._container = container
        
        # EventBus - The Primary Communication Channel
        self.bus = event_bus if event_bus else get_event_bus()
        
        # Expose Configuration Manager (Read-Only ideally, but direct for now)
        if container.config:
            self.config = FrozenProxy(container.config)
        else:
            self.config = None
        
    @property
    def container(self) -> Any:
        """
        [DEPRECATED] Access to the raw ServiceContainer.
        Plugins using this should be migrated to use specific Context APIs.
        """
        logger.warning(
            "Plugin is accessing raw 'context.container'. "
            "This is deprecated and will be removed in Phase 29. "
            "Please migrate to 'context.bus' or other safe APIs."
        )
        return self._container

    # --- Persistence API (Wraps SoulClient) ---
    # Plugins should use these methods instead of accessing soul_client directly
    
    def load_data(self, plugin_id: str) -> Dict:
        """Loads plugin-specific JSON data."""
        if self._container.soul_client:
             return self._container.soul_client.load_module_data(plugin_id)
        return {}

    def save_data(self, plugin_id: str, data: Dict):
        """Saves plugin-specific JSON data."""
        if self._container.soul_client:
             self._container.soul_client.save_module_data(plugin_id, data)

    def get_data_dir(self, plugin_id: str) -> Optional[str]:
        """Returns Path to plugin data directory for binary assets."""
        if self._container.soul_client:
             return self._container.soul_client.get_module_data_dir(plugin_id)
        return None

    def register_service(self, name: str, instance: Any):
        """
        Register a service via EventBus for plugin discovery.
        Also maintains backward compatibility by setting on container.
        
        Example: context.register_service('heartbeat_service', self)
        """
        # Register on EventBus (Phase 30 standard)
        self.bus.register_service(name, instance)
        
        # Backward compatibility: also set on container
        setattr(self._container, name, instance)
    
    @property
    def soul(self) -> Any:
        """Access to Soul Manager (Personality/State)."""
        return getattr(self._container, "soul_client", None)

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

    # --- Strict API Boundary (Phase 30) ---
    # Only allow access to explicitly defined public APIs.
    # This prevents plugins from depending on internal implementation details.
    
    # Whitelist of legacy attributes that are still allowed (for migration period)
    _ALLOWED_LEGACY_ATTRS = frozenset({"gateway"})
    
    def __getattr__(self, name: str):
        """
        Strict attribute access control.
        Only allows access to whitelisted legacy attributes.
        """
        # Private attributes are never accessible
        if name.startswith("_"):
            raise AttributeError(f"Private attribute '{name}' is not accessible")
        
        # Check whitelist for legacy access
        if name in self._ALLOWED_LEGACY_ATTRS:
            logger.warning(
                f"Plugin accessing legacy attribute '{name}'. "
                f"Please migrate to context.bus or other public APIs."
            )
            return getattr(self._container, name, None)
        
        # Deny access to non-public attributes
        raise AttributeError(
            f"'{name}' is not a public LuminaContext API. "
            f"Available APIs: bus, soul, ticker, memory, llm_manager, config, "
            f"load_data(), save_data(), get_data_dir(), register_service(), get_logger()"
        )

    # __setattr__ is intentionally NOT overridden to prevent plugins from
    # writing to arbitrary container attributes. Use register_service() instead.


