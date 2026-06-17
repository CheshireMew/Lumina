from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest


class CapabilityModuleLoader:
    def instantiate(self, manifest: CapabilityManifest) -> CapabilityModule:
        module_file = Path(manifest.path or "") / "module.py"
        if not module_file.exists():
            raise FileNotFoundError("module.py not found")

        module_package = f"lumina_capabilities.{manifest.id.replace('.', '_')}"
        module_name = f"{module_package}.module"

        self._ensure_package("lumina_capabilities")
        self._ensure_package(module_package, module_file.parent)

        spec = importlib.util.spec_from_file_location(module_name, module_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module spec for {manifest.id}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        module_cls = getattr(module, "Capability", None)
        if not isinstance(module_cls, type) or not issubclass(module_cls, CapabilityModule):
            raise TypeError(f"{manifest.id} must export class Capability")

        capability = module_cls()
        capability._bind_manifest(manifest)
        return capability

    def _ensure_package(self, package_name: str, package_path: Path | None = None):
        module = sys.modules.get(package_name)
        if module is None:
            module = types.ModuleType(package_name)
            module.__package__ = package_name
            module.__path__ = []
            sys.modules[package_name] = module

            parent_name, _, child_name = package_name.rpartition(".")
            if parent_name:
                parent = self._ensure_package(parent_name)
                setattr(parent, child_name, module)

        if package_path is not None:
            path_str = str(package_path)
            module_path = getattr(module, "__path__", [])
            if path_str not in module_path:
                module_path.append(path_str)
                module.__path__ = module_path

        return module
