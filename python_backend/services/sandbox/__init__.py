"""
Sandbox Package.
Provides plugin isolation, resource limiting, and permission control.
"""

from .resource_limiter import (
    ResourceLimiter,
    ResourceLimits,
    apply_sandbox_limits,
)

from .permission_guard import (
    Permission,
    PluginPermissions,
    PermissionGuard,
    create_guard_from_manifest,
)

__all__ = [
    # Resource Limiting
    'ResourceLimiter',
    'ResourceLimits',
    'apply_sandbox_limits',
    # Permissions
    'Permission',
    'PluginPermissions',
    'PermissionGuard',
    'create_guard_from_manifest',
]
