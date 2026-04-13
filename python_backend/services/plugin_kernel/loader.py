from __future__ import annotations

import importlib.util
import sys
import types
from pathlib import Path

from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest


class PluginLoader:
    def instantiate(self, manifest: PluginManifest) -> Plugin:
        plugin_file = Path(manifest.path or "") / "plugin.py"
        if not plugin_file.exists():
            raise FileNotFoundError("plugin.py not found")

        plugin_package = f"lumina_plugins.{manifest.id.replace('.', '_')}"
        module_name = f"{plugin_package}.plugin"

        self._ensure_package("lumina_plugins")
        self._ensure_package(plugin_package, plugin_file.parent)

        spec = importlib.util.spec_from_file_location(module_name, plugin_file)
        if spec is None or spec.loader is None:
            raise RuntimeError(f"Unable to load module spec for {manifest.id}")

        module = importlib.util.module_from_spec(spec)
        sys.modules[module_name] = module
        spec.loader.exec_module(module)

        plugin_cls = getattr(module, "Plugin", None)
        if not isinstance(plugin_cls, type) or not issubclass(plugin_cls, Plugin):
            raise TypeError(f"{manifest.id} must export class Plugin")

        plugin = plugin_cls()
        plugin._bind_manifest(manifest)
        return plugin

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
