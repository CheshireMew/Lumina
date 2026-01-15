"""
ServiceContainer - Dependency Injection Container
Refactored for explicit dependency management

Pattern: Service Locator + Typed Getters
- Core services registered at startup via setters
- Plugin services use EventBus.register_service() instead
- Runtime access via typed getters (with null checks)
"""
from typing import Optional, Any, TYPE_CHECKING, List

if TYPE_CHECKING:
    from routers.gateway import EventBus as WebSocketGateway
    from core.events.bus import EventBus
    from memory.core import SurrealMemory
    from llm.manager import LLMManager
    from memory.core import SurrealMemory
    from llm.manager import LLMManager
    from app_config import ConfigManager
    from core.interfaces.context import ContextProvider
    from core.interfaces.tool import ToolProvider
    from typing import List, Dict
    from typing import List


class ServiceNotInitializedError(Exception):
    """Raised when accessing a service that hasn't been initialized."""
    pass


class ServiceContainer:
    """
    Centralized service registry for CORE services only.
    
    Plugin services should use EventBus.register_service() instead.
    Access plugin services via: bus.get_service("service_name")
    
    Usage:
        # At startup (lifecycle.py):
        container.set_gateway(gateway_instance)
        
        # At runtime (anywhere):
        gateway = container.get_gateway()  # Raises if not initialized
    """
    _instance: Optional['ServiceContainer'] = None
    
    def __init__(self):
        # === CORE SERVICES (Infrastructure) ===
        self._gateway: Optional['WebSocketGateway'] = None
        self._event_bus: Optional['EventBus'] = None
        self._config: Optional['ConfigManager'] = None
        
        # === DATA SERVICES ===
        self._surreal_system: Optional['SurrealMemory'] = None
        self._llm_manager: Optional['LLMManager'] = None
        
        # === SYSTEM MANAGERS ===
        self._system_plugin_manager: Optional[Any] = None
        
        # === UTILITY SERVICES ===
        self._soul_client: Optional[Any] = None
        self._mcp_host: Optional[Any] = None
        self._batch_manager: Optional[Any] = None
        self._session_manager: Optional[Any] = None
        self._vision: Optional[Any] = None
        self._tts: Optional[Any] = None
        self._stt: Optional[Any] = None
        self._stt: Optional[Any] = None
        self._ticker: Optional[Any] = None
        
        # === REGISTRIES ===
        self._context_providers: List['ContextProvider'] = []
        self._tool_providers: Dict[str, 'ToolProvider'] = {}
        self._search_providers: Dict[str, Any] = {} # Keyed by ID

    # ==================== GETTERS (Typed, Null-Safe) ====================
    
    def get_gateway(self) -> 'WebSocketGateway':
        if self._gateway is None:
            raise ServiceNotInitializedError("Gateway not initialized. Check startup order.")
        return self._gateway
    
    def get_event_bus(self) -> 'EventBus':
        if self._event_bus is None:
            raise ServiceNotInitializedError("EventBus not initialized.")
        return self._event_bus
    
    def get_config(self) -> 'ConfigManager':
        if self._config is None:
            raise ServiceNotInitializedError("Config not initialized.")
        return self._config
    
    def get_surreal(self) -> 'SurrealMemory':
        if self._surreal_system is None:
            raise ServiceNotInitializedError("SurrealMemory not initialized.")
        return self._surreal_system
    
    def get_llm_manager(self) -> 'LLMManager':
        if self._llm_manager is None:
            raise ServiceNotInitializedError("LLMManager not initialized.")
        return self._llm_manager

    def get_vision(self) -> Any:
        if self._vision is None:
            raise ServiceNotInitializedError("VisionService not initialized.")
        return self._vision

    def get_tts(self) -> Any:
        if self._tts is None:
            raise ServiceNotInitializedError("TTSManager not initialized.")
        return self._tts

    # ==================== REGISTRY METHODS ====================
    
    def register_context_provider(self, provider: 'ContextProvider'):
        """Register a new context provider plugin."""
        self._context_providers.append(provider)
        
    def get_context_providers(self) -> List['ContextProvider']:
        """Get all registered providers."""
        return self._context_providers

    def register_tool_provider(self, provider: 'ToolProvider'):
        """Register a new tool provider."""
        self._tool_providers[provider.name] = provider

    def get_tool_provider(self, name: str) -> Optional['ToolProvider']:
        """Get a tool provider by name."""
        return self._tool_providers.get(name)

    def get_all_tools(self) -> List['ToolProvider']:
        """Get all registered tools."""
        return list(self._tool_providers.values())

    def register_search_provider(self, provider: Any):
        """Register a search provider (SearchProvider interface)."""
        self._search_providers[provider.id] = provider

    def get_search_provider(self, provider_id: str) -> Optional[Any]:
        return self._search_providers.get(provider_id)


    def get_stt(self) -> Any:
        if self._stt is None:
            raise ServiceNotInitializedError("STTManager not initialized.")
        return self._stt

    # ==================== SETTERS (For Lifecycle) ====================
    
    def set_gateway(self, instance: 'WebSocketGateway'):
        self._gateway = instance
    
    def set_event_bus(self, instance: 'EventBus'):
        self._event_bus = instance
    
    def set_config(self, instance: 'ConfigManager'):
        self._config = instance
    
    def set_surreal(self, instance: 'SurrealMemory'):
        self._surreal_system = instance
    
    def set_llm_manager(self, instance: 'LLMManager'):
        self._llm_manager = instance
        
    def set_vision(self, instance: Any):
        self._vision = instance

    def set_tts(self, instance: Any):
        self._tts = instance

    # ==================== LEGACY PROPERTIES (Backward Compat) ====================
    # These are kept for existing code that uses services.xxx syntax
    
    @property
    def gateway(self):
        return self._gateway
    
    @gateway.setter
    def gateway(self, value):
        self._gateway = value
    
    @property
    def event_bus(self):
        return self._event_bus
    
    @event_bus.setter
    def event_bus(self, value):
        self._event_bus = value
    
    @property
    def config(self):
        return self._config
    
    @config.setter
    def config(self, value):
        self._config = value
    
    @property
    def surreal_system(self):
        return self._surreal_system
    
    @surreal_system.setter
    def surreal_system(self, value):
        self._surreal_system = value
    
    @property
    def llm_manager(self):
        return self._llm_manager
    
    @llm_manager.setter
    def llm_manager(self, value):
        self._llm_manager = value
    
    @property
    def system_plugin_manager(self):
        return self._system_plugin_manager
    
    @system_plugin_manager.setter
    def system_plugin_manager(self, value):
        self._system_plugin_manager = value
    
    @property
    def soul_client(self):
        return self._soul_client
    
    @soul_client.setter
    def soul_client(self, value):
        self._soul_client = value
    
    @property
    def mcp_host(self):
        return self._mcp_host
    
    @mcp_host.setter
    def mcp_host(self, value):
        self._mcp_host = value
    
    @property
    def batch_manager(self):
        return self._batch_manager
    
    @batch_manager.setter
    def batch_manager(self, value):
        self._batch_manager = value
    
    @property
    def session_manager(self):
        return self._session_manager
    
    @session_manager.setter
    def session_manager(self, value):
        self._session_manager = value
    
    @property
    def vision(self):
        return self._vision
    
    @vision.setter
    def vision(self, value):
        self._vision = value
    
    @property
    def ticker(self):
        return self._ticker
    
    @ticker.setter
    def ticker(self, value):
        self._ticker = value

    @property
    def stt(self):
        return self._stt
    
    @stt.setter
    def stt(self, value):
        self._stt = value

    # ==================== SINGLETON ====================
    
    @classmethod
    def get_instance(cls) -> 'ServiceContainer':
        if cls._instance is None:
            cls._instance = ServiceContainer()
        return cls._instance


# Global singleton (legacy compat)
services = ServiceContainer.get_instance()
