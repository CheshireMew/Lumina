from __future__ import annotations

import logging
import hashlib
import importlib.util
import sys
import types
from pathlib import Path
from typing import Type

from core.manifest import CapabilityManifest, read_manifest_file
from core.runtime import normalize_runtime_target
from security.policy import SecurityPolicy

logger = logging.getLogger("DriverLoader")


class DriverLoader:
    @staticmethod
    def _package_name(directory: Path) -> str:
        digest = hashlib.sha1(
            str(directory.resolve()).encode("utf-8"),
        ).hexdigest()[:12]
        return f"lumina_dynamic_drivers.{digest}"

    @staticmethod
    def _ensure_package(package_name: str, directory: Path) -> None:
        root_name = "lumina_dynamic_drivers"
        root_module = sys.modules.get(root_name)
        if root_module is None:
            root_module = types.ModuleType(root_name)
            root_module.__path__ = []
            sys.modules[root_name] = root_module

        package_module = sys.modules.get(package_name)
        if package_module is None:
            package_module = types.ModuleType(package_name)
            package_module.__path__ = [str(directory)]
            sys.modules[package_name] = package_module

    @staticmethod
    def load_plugins(directory: str | Path, base_class: Type, recursive: bool = False) -> list:
        directory = Path(directory)
        if not directory.exists():
            return []

        logger.info("Scanning driver directory: %s", directory)
        instances = []
        files = list(directory.rglob("*.py")) if recursive else list(directory.glob("*.py"))
        package_name = DriverLoader._package_name(directory)
        DriverLoader._ensure_package(package_name, directory)

        for entry in files:
            if entry.name == "__init__.py":
                continue

            module_name = f"{package_name}.{entry.stem}"
            try:
                spec = importlib.util.spec_from_file_location(module_name, entry)
                if not spec or not spec.loader:
                    continue

                module = importlib.util.module_from_spec(spec)
                sys.modules[module_name] = module
                spec.loader.exec_module(module)

                for obj in vars(module).values():
                    if (
                        isinstance(obj, type)
                        and issubclass(obj, base_class)
                        and obj is not base_class
                        and obj.__module__ == module.__name__
                    ):
                        instances.append(obj())
            except Exception as exc:
                logger.warning("Failed to load driver module %s: %s", entry.name, exc)

        return instances


def allow_extension_driver(manifest_path: Path, capability: str, runtime_target: str) -> tuple[bool, CapabilityManifest | None]:
    if not manifest_path.exists():
        return (False, None)

    raw = read_manifest_file(manifest_path)
    manifest = CapabilityManifest(**{**raw, "path": str(manifest_path.parent)})
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
