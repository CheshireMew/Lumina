from abc import ABC, abstractmethod
from typing import Any

class BaseSystemPlugin(ABC):
    """
    Abstract base class for all System Plugins.
    Plugins must inherit from this and implement the `initialize` method.
    """
    
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
    def router(self) -> Any:
        """
        Optional Router for the plugin.
        """
        return None
    
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

    def initialize(self, context: Any):
        """
        Called when the plugin is loaded.
        :param context: The LuminaContext instance (replaces container).
        """
        self.context = context
        self._router_registered = False  # Track if router was registered via EventBus

    def terminate(self):
        """
        Called before the plugin is unloaded or reloaded.
        Override this to cleanup resources (threads, sockets, listeners).
        """
        pass

    def register_router(self, router, prefix: str = None):
        """
        Register a FastAPI router via EventBus (Phase 30 standard).
        This decouples plugins from direct FastAPI app access.
        
        Args:
            router: The FastAPI APIRouter instance
            prefix: URL prefix (default: /plugins/{plugin_id})
        """
        if not hasattr(self, 'context') or not self.context:
            raise RuntimeError("Cannot register router before initialize() is called")
        
        if not prefix:
            prefix = f"/plugins/{self.id}"
        
        self.context.bus.emit_sync("core.register_router", {
            "router": router,
            "prefix": prefix
        })
        self._router_registered = True

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

        return {
            "id": self.id,
            "category": getattr(self, "category", "system"), # Use property or default
            "name": self.name,
            "description": getattr(self, "description", ""),
            "enabled": self.enabled,
            "permissions": getattr(self, "_manifest", None).permissions if getattr(self, "_manifest", None) else [],
            "active_in_group": False, # Default
            # Attempt to find config schema or group id if defined as properties
            "config_schema": schema,
            "current_value": current_val, # Auto-populated from config
            "config": self.config,        # Full config for multi-field forms
            "group_id": getattr(self, "group_id", getattr(getattr(self, "_manifest", None), "group_id", None)),
            "group_exclusive": getattr(self, "group_exclusive", getattr(getattr(self, "_manifest", None), "group_exclusive", True)),
            "func_tag": getattr(self, "func_tag", "System Plugin"),
            "llm_routes": getattr(self, "llm_routes", []), # ⚡ New: Expose LLM routes to Frontend
            "tags": getattr(self, "_manifest", None).tags if getattr(self, "_manifest", None) else []
        }
