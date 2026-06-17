from __future__ import annotations

import logging

from core.manifest import CapabilityManifest
from security.policy import SecurityPolicy

logger = logging.getLogger("CapabilityPermissionChecker")


class CapabilityPermissionError(Exception):
    pass


class PermissionChecker:
    def ensure_allowed(self, manifest: CapabilityManifest) -> None:
        allowed, warnings = SecurityPolicy.check_permissions(manifest)
        for warning in warnings:
            logger.warning("[%s] %s", manifest.id, warning)
        if not allowed:
            raise CapabilityPermissionError("permission_check_failed")
