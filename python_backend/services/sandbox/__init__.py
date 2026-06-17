"""
Sandbox Package.
Provides capability module isolation, resource limiting, and permission control.
"""

from .resource_limiter import (
    ResourceLimiter,
    ResourceLimits,
    apply_sandbox_limits,
)

from .permission_guard import (
    CapabilityModulePermissions,
    Permission,
    PermissionGuard,
    create_guard_from_manifest,
)

__all__ = [
    # Resource Limiting
    'ResourceLimiter',
    'ResourceLimits',
    'apply_sandbox_limits',
    # Permissions
    'CapabilityModulePermissions',
    'Permission',
    'PermissionGuard',
    'create_guard_from_manifest',
]
