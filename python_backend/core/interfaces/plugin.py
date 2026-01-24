from abc import ABC, abstractmethod
from typing import Any
from core.api_version import api_stable, PLUGIN_API_VERSION

class BaseSystemPlugin(ABC):
    """
    Abstract base class for all System Plugins.
    Plugins must inherit from this and implement the `initialize` method.
    
    API Version: 1.0 (Stable)
    """
    
    # Expose API version for plugins to check
    API_VERSION = PLUGIN_API_VERSION
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique Identifier for the plugin (e.g., 'voiceprint-manager')"""
        pass

    @property
    @abstractmethod
    def name(self) -> str:
        """Human-readable name"""
        pass


    @property
    def llm_routes(self) -> list[str]:
        """
        List of LLM Route Features this plugin requires.
        e.g. ["dreaming", "memory"]
        SystemPluginManager will register these with LLMManager automatically.
        """
        return []

    @property
    def enabled(self) -> bool:
        """
        Whether the plugin is enabled. Reads from config, defaults to True.
        """
        return self.config.get("enabled", True)

    @enabled.setter
    def enabled(self, value: bool):
        self.update_config("enabled", value)

    @api_stable("1.0")
    def initialize(self, context: Any):
        """
        Called when the plugin is loaded.
        :param context: The LuminaContext instance (replaces container).
        
        API: Stable since 1.0
        """
        self.context = context
        self._router_registered = False  # Track if router was registered via EventBus

    @api_stable("1.0")
    def terminate(self):
        """
        Called before the plugin is unloaded or reloaded.
        Override this to cleanup resources (threads, sockets, listeners).
        
        API: Stable since 1.0
        """
        pass

    def register_route(self, path: str, method: str, handler: Any, response_model: Any = None):
        """
        Register a generic API route (Decoupled from FastAPI).
        
        Args:
            path: URL path (e.g., "/status") - Will be prefixed with /plugins/{id}
            method: HTTP Method ("GET", "POST", etc.)
            handler: Python callable (async def)
            response_model: Optional Pydantic model for response validation
        """
        if not hasattr(self, 'context') or not self.context:
            raise RuntimeError("Cannot register route before initialize() is called")
        
        # Resolve handler name for RPC mapping
        handler_name = getattr(handler, "__name__", str(handler))

        # Emit generic route definition event
        # DELEGATE TO CONTEXT (Abstraction Layer)
        # This allows Context to decide between Direct Injection (RouterManager) or EventBus (RPC)
        if hasattr(self.context, 'register_route_def'):
            self.context.register_route_def(
                path=path,
                method=method.upper(),
                handler_name=handler_name,
                handler=handler
            )
        else:
            # Fallback for old context mocks?
            self.context.bus.emit_sync("core.register_route_def", {
                "plugin_id": self.id,
                "path": path,
                "method": method.upper(),
                "handler": handler,
                "handler_name": handler_name,
                "response_model": response_model
            })

    # ================= Persistence Helpers (Phase 28) =================
    # Plugins must set self.context in initialize() to use these.

    def load_data(self) -> dict:
        """Loads plugin-specific JSON data via Context API"""
        if hasattr(self, "context") and self.context:
            return self.context.load_data(self.id)
        # No fallback: Enforcement
        return {}

    def save_data(self, data: dict):
        """Saves plugin-specific JSON data via Context API"""
        if hasattr(self, "context") and self.context:
            self.context.save_data(self.id, data)

    def get_data_dir(self):
        """Returns Path to characters/{id}/data/{plugin_id}/ for binary assets."""
        if hasattr(self, "context") and self.context:
            return self.context.get_data_dir(self.id)
        return None

    # ================= Config System (Phase 13) =================

    @property
    def config(self) -> dict:
        """
        Auto-persisted configuration dictionary.
        Lazy-loads from data/{plugin_id}.json on first access.
        """
        if not hasattr(self, "_config_cache"):
            self._config_cache = self.load_data() or {}
        return self._config_cache

    def update_config(self, key: str, value: Any):
        """Updates a config value and persists to disk immediately."""
        cfg = self.config
        cfg[key] = value
        self.save_data(cfg)
        self._config_cache = cfg # Update cache

    def get_status(self) -> dict:
        """
        Returns the plugin status dictionary for the frontend.
        """
        # Determine current value if schema is present (single-field support)
        current_val = ""
        schema = getattr(self, "config_schema", None)
        if schema and "key" in schema:
             current_val = self.config.get(schema["key"], getattr(self, "current_value", ""))


        # [FIX] Manifest Inheritance Helper
        manifest = getattr(self, "_manifest", None)
        
        def get_meta(key, default):
            # 1. Instance Property (Code Override)
            if hasattr(self, key): 
                return getattr(self, key)
            # 2. Manifest (Configuration)
            if manifest and hasattr(manifest, key):
                val = getattr(manifest, key)
                if val: return val
            # 3. Default
            return default

        return {
            "id": self.id,
            "category": get_meta("category", "system"),
            "name": self.name,
            "description": get_meta("description", ""),
            "enabled": self.enabled,
            "permissions": manifest.permissions if manifest else [],
            "active_in_group": False, # Default
            # Attempt to find config schema or group id if defined as properties
            "config_schema": schema or get_meta("config_schema", None),
            "ui_slots": get_meta("ui_slots", []),
            "current_value": current_val, # Auto-populated from config
            "config": self.config,        # Full config for multi-field forms
            
            "group_id": get_meta("group_id", None),
            "group_exclusive": get_meta("group_exclusive", True),
            "func_tag": get_meta("func_tag", "System Plugin"),
            
            "llm_routes": getattr(self, "llm_routes", []), 
            "tags": manifest.tags if manifest else []
        }
