import logging
from typing import List, Tuple
from core.manifest import PluginManifest
from core.permissions import TIER_SAFE, TIER_TRUSTED, TIER_SYSTEM
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
        
        # Normalize permissions in the manifest dynamically for this check
        # (We don't modify the manifest object here, just the list we check)
        requested_perms = [SecurityPolicy.normalize_permission(p) for p in manifest.permissions]
        
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
        
        # Policy Logic
        is_system_plugin = manifest.id.startswith("system.") or manifest.id.startswith("driver.")
        
        if manifest.isolation_mode == "local" and is_risky:
            if is_system_plugin:
                # System/Driver plugins are allowed to run locally with high privs
                AuditLogger.log_event_sync(
                    actor_id=manifest.id,
                    action="permission_check",
                    target="system.local_execution",
                    status="granted",
                    metadata={"permissions": requested_perms, "warnings": warnings}
                )
                return True, warnings
            else:
                # Dangerous: Community Plugin requests SYSTEM permissions in LOCAL capability
                logger.error(f"⛔ SECURITY BLOCK: Plugin '{manifest.id}' requests SYSTEM permissions in LOCAL mode.")
                AuditLogger.log_event_sync(
                    actor_id=manifest.id,
                    action="permission_check",
                    target="system.local_execution",
                    status="blocked",
                    metadata={"permissions": requested_perms, "warnings": warnings}
                )
                return False, warnings
            
        return True, warnings 

    @staticmethod
    def enforce_isolation_policy(manifest: PluginManifest) -> PluginManifest:
        """
        [Hardening] Force 'process' isolation for community plugins (non-system).
        This modifies the manifest in-place if needed (or we returns a copy).
        """
        is_system = manifest.id.startswith("system.") or manifest.id.startswith("driver.")
        
        if not is_system and manifest.isolation_mode == "local":
            logger.warning(f"🔒 Enforcing Isolation: Plugin '{manifest.id}' switched to PROCESS mode (Community plugins cannot run locally).")
            manifest.isolation_mode = "process"
            
        return manifest
