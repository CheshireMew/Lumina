from __future__ import annotations

import logging
import os
from dataclasses import dataclass, field
from pathlib import Path

from core.manifest import CapabilityManifest, read_manifest_file
from core.runtime import normalize_runtime_target

logger = logging.getLogger("CapabilityManifestRepository")


@dataclass
class ManifestDiscoveryResult:
    manifests: dict[str, CapabilityManifest] = field(default_factory=dict)
    errors: dict[str, str] = field(default_factory=dict)


class ManifestRepository:
    def __init__(self, module_root: Path):
        self.module_root = Path(module_root)

    def discover(self, runtime_target: str) -> ManifestDiscoveryResult:
        result = ManifestDiscoveryResult()
        normalized_target = normalize_runtime_target(runtime_target)

        seen_paths: set[Path] = set()
        module_roots = [self.module_root, *self._extra_module_roots()]
        for module_root in module_roots:
            if not module_root.exists():
                continue

            for module_dir in module_root.iterdir():
                if not self._is_module_dir(module_dir):
                    continue
                resolved_module_dir = module_dir.resolve()
                if resolved_module_dir in seen_paths:
                    continue
                seen_paths.add(resolved_module_dir)

                manifest_path = module_dir / "manifest.yaml"
                if not manifest_path.exists():
                    continue

                try:
                    manifest = self._read_manifest(manifest_path, module_dir)
                except Exception as exc:
                    result.errors[module_dir.name] = f"manifest invalid: {exc}"
                    logger.error("Failed to parse manifest %s: %s", manifest_path, exc)
                    continue

                if normalize_runtime_target(manifest.runtime_target) != normalized_target:
                    continue

                result.manifests[manifest.id] = manifest

        return result

    @staticmethod
    def _extra_module_roots() -> list[Path]:
        raw_roots = os.environ.get("LUMINA_CAPABILITY_MODULE_ROOTS", "")
        roots: list[Path] = []
        for raw_root in raw_roots.split(os.pathsep):
            if not raw_root.strip():
                continue
            root = Path(raw_root).resolve()
            if root.exists():
                roots.append(root)
        return roots

    @staticmethod
    def _is_module_dir(module_dir: Path) -> bool:
        return module_dir.is_dir() and not module_dir.name.startswith(("_", "."))

    @staticmethod
    def _read_manifest(manifest_path: Path, module_dir: Path) -> CapabilityManifest:
        raw = read_manifest_file(manifest_path)
        return CapabilityManifest(**{**raw, "path": str(module_dir)})
