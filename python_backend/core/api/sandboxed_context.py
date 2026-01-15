"""
Lumina Sandboxed Context
Security & Sandboxing

Wraps LuminaContext with permission-based access control.
Plugins receive a SandboxedContext if they have restricted permissions.
"""

import logging
from typing import Any, Optional, Dict, Set, List

from .context import LuminaContext
from core.permissions import Permission, DEFAULT_PERMISSIONS

logger = logging.getLogger("SandboxedContext")


class PermissionError(Exception):
    """Raised when a plugin attempts to access a resource without permission."""
    pass


class SandboxedContext(LuminaContext):
    """
    A permission-checked wrapper around LuminaContext.
    
    Each API call is gated by permission checks. If a plugin lacks
    the required permission, a PermissionError is raised.
    
    Usage:
        context = SandboxedContext(container, event_bus, permissions=["memory.read", "llm.invoke"])
        
        # This works:
        data = context.memory.query(...)
        
        # This raises PermissionError:
        context.memory.write(...)  # Lacks "memory.write" permission
    """
    
    def __init__(self, container: Any, event_bus=None, permissions: List[str] = None):
        super().__init__(container, event_bus)
        
        # Combine default + requested permissions
        self._permissions: Set[str] = set(DEFAULT_PERMISSIONS)
        if permissions:
            self._permissions.update(permissions)
        
        logger.debug(f"馃敀 SandboxedContext created with permissions: {self._permissions}")
    
    def _check_permission(self, perm: str, action: str = "access this resource"):
        """
        Check if the plugin has the required permission.
        
        Args:
            perm: The permission string to check
            action: Description of what action requires this permission
        
        Raises:
            PermissionError: If permission is not granted
        """
        if perm not in self._permissions:
            raise PermissionError(
                f"Plugin lacks '{perm}' permission required to {action}. "
                f"Add '{perm}' to permissions in manifest.yaml."
            )
    
    @property
    def permissions(self) -> Set[str]:
        """Return the set of granted permissions (read-only)."""
        return frozenset(self._permissions)
    
    def has_permission(self, perm: str) -> bool:
        """Check if a permission is granted."""
        return perm in self._permissions
    
    # --- Permission-Gated Properties ---
    
    @property
    def memory(self) -> Any:
        """Access to Memory System (requires memory.read permission)."""
        self._check_permission(Permission.MEMORY_READ.value, "read from memory system")
        return super().memory
    
    @property
    def llm_manager(self) -> Any:
        """Access to LLM Manager (requires llm.invoke permission)."""
        self._check_permission(Permission.LLM_INVOKE.value, "invoke LLM")
        return super().llm_manager
    
    @property
    def ticker(self) -> Any:
        """Access to Global Ticker (requires ticker.subscribe permission)."""
        self._check_permission(Permission.TICKER_SUBSCRIBE.value, "subscribe to ticker")
        return super().ticker
    
    # --- Permission-Gated Methods ---
    
    def save_data(self, plugin_id: str, data: Dict):
        """Saves plugin-specific JSON data (requires filesystem.write)."""
        self._check_permission(Permission.FILESYSTEM_WRITE.value, "write plugin data")
        super().save_data(plugin_id, data)
    
    def get_data_dir(self, plugin_id: str) -> Optional[str]:
        """Returns Path to plugin data directory (requires filesystem.read)."""
        self._check_permission(Permission.FILESYSTEM_READ.value, "access data directory")
        return super().get_data_dir(plugin_id)
    
    # --- Non-Gated APIs (available to all plugins) ---
    # These inherit from LuminaContext without additional checks:
    # - bus (EventBus - with event.subscribe/event.emit defaults)
    # - soul (read-only access to character state)
    # - config (read-only configuration)
    # - load_data() (read plugin's own data)
    # - register_service() (expose plugin capabilities)
    # - get_logger() (logging)
