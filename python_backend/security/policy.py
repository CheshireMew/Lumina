import logging
from typing import List, Tuple
from core.manifest import PluginManifest
from core.permissions import TIER_SAFE, TIER_TRUSTED, TIER_SYSTEM, validate_permissions
from core.security.audit import AuditLogger

logger = logging.getLogger("SecurityPolicy")

class SecurityPolicy:
    """
    Enforces permission checks for plugins.
    """
    
    @staticmethod
    def normalize_permission(perm: str) -> str:
        """
        Convert legacy syntax (colon) to new syntax (dot).
        e.g. 'os:exec' -> 'os.exec'
        """
        if ":" in perm:
            # Simple heuristic mapping or direct replacement
            return perm.replace(":", ".")
        return perm

    @staticmethod
    def check_permissions(manifest: PluginManifest) -> Tuple[bool, List[str]]:
        """
        Check if plugin permissions are acceptable.
        Returns: (is_allowed, warnings)
        """
        warnings = []
        is_risky = False
        invalid_permissions = []
        
        # Normalize permissions in the manifest dynamically for this check
        # (We don't modify the manifest object here, just the list we check)
        requested_perms = [SecurityPolicy.normalize_permission(p) for p in manifest.permissions]
        invalid_permissions = validate_permissions(requested_perms)
        if invalid_permissions:
            warnings.append(f"❌ Invalid permissions: {', '.join(invalid_permissions)}")
        
        for perm in requested_perms:
            # TIER_* lists contain strings (Enum.value)
            if perm in TIER_SYSTEM:
                warnings.append(f"🔴 System Permission Requested: {perm}")
                is_risky = True
            elif perm in TIER_TRUSTED:
                warnings.append(f"🟡 Trusted Permission Requested: {perm}")
            elif perm not in TIER_SAFE:
                # Check known safe/default permissions from permissions.py if needed
                # For now, treat unknown as warning
                warnings.append(f"❓ Unknown Permission: {perm}")
                invalid_permissions.append(perm)
        
        # Policy Logic
        if is_risky or invalid_permissions:
            AuditLogger.log_event_sync(
                actor_id=manifest.id,
                action="permission_check",
                target="plugin.permissions",
                status="warning",
                metadata={
                    "permissions": requested_perms,
                    "warnings": warnings,
                    "invalid_permissions": invalid_permissions,
                }
            )
        return (not is_risky and not invalid_permissions), warnings

    @staticmethod
    def enforce_isolation_policy(manifest: PluginManifest) -> PluginManifest:
        """
        Compatibility no-op: isolation mode was removed from the unified contract.
        """
        return manifest
