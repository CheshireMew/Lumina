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
    
    def __init__(self, container: Any, plugin_id: str, event_bus=None, permissions: List[str] = None, router_manager=None):
        super().__init__(container, plugin_id, event_bus=event_bus, router_manager=router_manager)
        
        # Combine default + requested permissions (Ensure strings)
        defaults = {p.value if hasattr(p, 'value') else str(p) for p in DEFAULT_PERMISSIONS}
        self._permissions: Set[str] = defaults
        if permissions:
            self._permissions.update({p.value if hasattr(p, 'value') else str(p) for p in permissions})
        
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
            # [Architecture 6.0] Audit Denial
            self.audit("access_check", f"permission:{perm}", "denied", metadata={"reason": action})
            
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
    
    def find_capability(self, cap_type: str, **attributes) -> Optional[str]:
        """Discovery API (requires plugin.discovery permission)."""
        self._check_permission(Permission.PLUGIN_DISCOVERY.value, "find capability providers")
        return super().find_capability(cap_type, **attributes)

    def register_route_def(self, path: str, method: str, handler_name: str, handler: Any):
        """Register API route (requires network.listen permission)."""
        # [Security] Prevent arbitrary port/route exposure
        self._check_permission(Permission.NETWORK_LISTEN.value, "register API route")
        return super().register_route_def(path, method, handler_name, handler)

    # --- Permission-Gated Methods ---
    
    def load_data(self, plugin_id: str) -> Dict:
        """Loads plugin-specific JSON data (Strict Isolation)."""
        if plugin_id != self.plugin_id:
            # [Security] Prevent Cross-Plugin Data Access
            self.audit("access_check", f"read_data:{plugin_id}", "denied", metadata={"reason": "cross-plugin access"})
            raise PermissionError("Sandboxed plugins can only load their own data.")
            
        # Permission Check (Self-Data read doesn't technically need extra permission beyond default, 
        # but let's require filesystem.read per spec if strictly interpreted? 
        # Actually legacy 'filesystem.read' meant OWN data. So yes.)
        self._check_permission(Permission.FILESYSTEM_READ.value, "read plugin data")
        return super().load_data(plugin_id)

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
