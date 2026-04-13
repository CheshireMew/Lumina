from __future__ import annotations

import logging

from core.manifest import PluginManifest
from security.policy import SecurityPolicy

logger = logging.getLogger("PluginPermissionChecker")


class PluginPermissionError(Exception):
    pass


class PermissionChecker:
    def ensure_allowed(self, manifest: PluginManifest) -> None:
        allowed, warnings = SecurityPolicy.check_permissions(manifest)
        for warning in warnings:
            logger.warning("[%s] %s", manifest.id, warning)
        if not allowed:
            raise PluginPermissionError("permission_check_failed")
