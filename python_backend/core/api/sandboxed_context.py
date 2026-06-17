"""
Lumina Sandboxed Context
Security & Sandboxing

Wraps LuminaContext with permission-based access control.
Capability modules receive a SandboxedContext if they have restricted permissions.
"""

import logging
from pathlib import Path
from typing import Any, Optional, Set, List

from .context import LuminaContext
from core.permissions import Permission, DEFAULT_PERMISSIONS
from core.services.service_registry import ServiceRegistry

logger = logging.getLogger("SandboxedContext")


class PermissionError(Exception):
    """Raised when a capability module attempts to access a resource without permission."""
    pass


class SandboxedContext(LuminaContext):
    """
    A permission-checked wrapper around LuminaContext.
    
    Each API call is gated by permission checks. If a module lacks
    the required permission, a PermissionError is raised.
    
    Usage:
        context = SandboxedContext(container, event_bus, permissions=["memory.read", "llm.invoke"])
        
        # This works:
        data = context.memory.query(...)
        
        # This raises PermissionError:
        context.memory.write(...)  # Lacks "memory.write" permission
    """
    
    def __init__(
        self,
        container: Any,
        module_id: str,
        manifest: Any = None,
        event_bus=None,
        permissions: List[str] = None,
        service_registry: ServiceRegistry | None = None,
    ):
        super().__init__(
            container,
            module_id,
            manifest,
            event_bus=event_bus,
            service_registry=service_registry,
        )
        
        # Combine default + requested permissions (Ensure strings)
        defaults = {p.value if hasattr(p, 'value') else str(p) for p in DEFAULT_PERMISSIONS}
        self._permissions: Set[str] = defaults
        if permissions:
            self._permissions.update({p.value if hasattr(p, 'value') else str(p) for p in permissions})
        
        logger.debug(f"馃敀 SandboxedContext created with permissions: {self._permissions}")
    
    def _log_denial(self, perm: str, action: str):
        logger.warning(
            "Sandboxed capability module %s denied permission %s while trying to %s",
            self.module_id,
            perm,
            action,
        )

    def _check_permission(self, perm: str, action: str = "access this resource"):
        """
        Check if the module has the required permission.
        
        Args:
            perm: The permission string to check
            action: Description of what action requires this permission
        
        Raises:
            PermissionError: If permission is not granted
        """
        if perm not in self._permissions:
            self._log_denial(perm, action)
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
        return self.get_service("memory")
    
    @property
    def llm_manager(self) -> Any:
        """Access to LLM Manager (requires llm.invoke permission)."""
        self._check_permission(Permission.LLM_INVOKE.value, "invoke LLM")
        return self.get_service("llm_manager")
    
    @property
    def ticker(self) -> Any:
        """Access to Global Ticker (requires ticker.subscribe permission)."""
        self._check_permission(Permission.TICKER_SUBSCRIBE.value, "subscribe to ticker")
        return self.get_service("ticker")
    
    def find_capability(self, cap_type: str, **attributes) -> Optional[str]:
        """Discovery API (requires capability.discovery permission)."""
        self._check_permission(Permission.CAPABILITY_DISCOVERY.value, "find capability providers")
        return super().find_capability(cap_type, **attributes)

    # --- Permission-Gated Methods ---
    
    def load_data(self) -> dict[str, Any]:
        """Load the module's own persisted data."""
        self._check_permission(Permission.FILESYSTEM_DATA_READ.value, "read module data")
        return super().load_data()

    def save_data(self, data: dict[str, Any]):
        """Persist the module's own data."""
        self._check_permission(Permission.FILESYSTEM_DATA_WRITE.value, "write module data")
        super().save_data(data)
    
    def get_data_dir(self) -> Path | None:
        """Return the module's data directory."""
        self._check_permission(Permission.FILESYSTEM_DATA_READ.value, "access data directory")
        return super().get_data_dir()
    
    # --- Non-Gated APIs (available to all modules) ---
    # These inherit from LuminaContext without additional checks:
    # - bus (EventBus - with event.subscribe/event.emit defaults)
    # - soul (read-only access to character state)
    # - config (read-only configuration)
    # - load_data() (read module data)
    # - get_logger() (logging)
