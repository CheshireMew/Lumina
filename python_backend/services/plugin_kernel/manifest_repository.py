from __future__ import annotations

import logging
from dataclasses import dataclass, field
from pathlib import Path

import yaml

from core.manifest import PluginManifest
from core.runtime import normalize_runtime_target

logger = logging.getLogger("PluginManifestRepository")


@dataclass
class ManifestDiscoveryResult:
    manifests: dict[str, PluginManifest] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class ManifestRepository:
    def __init__(self, plugin_root: Path):
        self.plugin_root = Path(plugin_root)

    def discover(self, runtime_target: str) -> ManifestDiscoveryResult:
        result = ManifestDiscoveryResult()
        normalized_target = normalize_runtime_target(runtime_target)

        for root_name in ("system", "extensions"):
            root_dir = self.plugin_root / root_name
            if not root_dir.exists():
                continue

            for plugin_dir in root_dir.iterdir():
                if not self._is_plugin_dir(plugin_dir):
                    continue

                manifest_path = plugin_dir / "manifest.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = self._read_manifest(manifest_path, plugin_dir)
                except Exception as exc:
                    result.errors[plugin_dir.name] = f"manifest invalid: {exc}"
                    logger.error("Failed to parse manifest %s: %s", manifest_path, exc)
                    continue

                if normalize_runtime_target(manifest.runtime_target) != normalized_target:
                    continue

                result.manifests[manifest.id] = manifest

        return result

    @staticmethod
    def _is_plugin_dir(plugin_dir: Path) -> bool:
        return plugin_dir.is_dir() and not plugin_dir.name.startswith(("_", "."))

    @staticmethod
    def _read_manifest(manifest_path: Path, plugin_dir: Path) -> PluginManifest:
        with open(manifest_path, "r", encoding="utf-8") as fh:
            raw = yaml.safe_load(fh) or {}
        return PluginManifest(**{**raw, "path": str(plugin_dir)})
