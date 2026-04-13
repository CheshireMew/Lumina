from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import yaml

from core.manifest import PluginManifest
from core.runtime import normalize_runtime_target
from security.policy import SecurityPolicy

logger = logging.getLogger("DriverLoader")


def allow_extension_driver(manifest_path: Path, capability: str, runtime_target: str) -> tuple[bool, PluginManifest | None]:
    if not manifest_path.exists():
        return (False, None)

    raw = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
    manifest = PluginManifest(**{**raw, "path": str(manifest_path.parent)})
    allowed, warnings = SecurityPolicy.check_permissions(manifest)
    for warning in warnings:
        logger.warning("[%s] %s", manifest.id, warning)

    if not allowed:
        return (False, manifest)

    if manifest.capability != capability:
        return (False, manifest)

    if normalize_runtime_target(manifest.runtime_target) != normalize_runtime_target(runtime_target):
        return (False, manifest)

    return (True, manifest)
