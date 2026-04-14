from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from config.paths import BASE_DIR, DATA_ROOT, IS_FROZEN


STATUS_READY = "ready"
STATUS_UNAVAILABLE = "unavailable"
STATUS_FAILED = "failed"


def _normalize_version(value: str | None) -> tuple[int, ...]:
    if not value:
        return (0,)
    parts: list[int] = []
    for raw in value.split("."):
        digits = "".join(ch for ch in raw if ch.isdigit())
        parts.append(int(digits or 0))
    return tuple(parts or [0])


def _version_gte(left: str | None, right: str | None) -> bool:
    return _normalize_version(left) >= _normalize_version(right)


def _runtime_roots() -> dict[str, Path]:
    executable_dir = Path(sys.executable).resolve().parent
    env_resources = os.environ.get("LUMINA_RESOURCES_DIR")
    resources_dir = Path(env_resources).resolve() if env_resources else (
        executable_dir.parent.parent if IS_FROZEN else BASE_DIR.parent
    )
    return {
        "project": BASE_DIR if IS_FROZEN else BASE_DIR.parent,
        "backend": BASE_DIR,
        "data": DATA_ROOT,
        "resources": resources_dir,
        "executable": executable_dir,
    }


def _expand_path(value: str | None, roots: dict[str, Path]) -> Path | None:
    if not value:
        return None

    expanded = value
    for key, root in roots.items():
        expanded = expanded.replace(f"${{{key}}}", str(root))
    return Path(expanded).resolve()


def _normalize_arch(value: str | None) -> str:
    normalized = (value or "").strip().lower()
    if normalized in {"amd64", "x86_64"}:
        return "x64"
    return normalized


@dataclass(frozen=True)
class CapabilityPackageSource:
    name: str
    root: str
    entry_executable: str | None = None
    entry_arguments: tuple[str, ...] = ()
    required_files: tuple[str, ...] = ()
    resource_dirs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class CapabilityPackageDefinition:
    id: str
    version: str
    min_host_version: str
    min_package_version: str
    install_dir: str
    package_type: str
    entry_executable: str | None
    entry_arguments: tuple[str, ...]
    health_endpoint: str | None
    required_files: tuple[str, ...]
    resource_dirs: dict[str, str]
    platform: tuple[str, ...]
    arch: tuple[str, ...]
    auto_start: bool
    optional: bool
    display_name: str
    failure_mode: str
    capabilities: tuple[str, ...]
    sources: tuple[CapabilityPackageSource, ...] = ()


@dataclass(frozen=True)
class ResolvedCapabilityPackage:
    definition: CapabilityPackageDefinition
    status: str
    source_name: str | None
    root_dir: Path | None
    entry_executable: Path | None
    entry_arguments: tuple[str, ...]
    resource_dirs: dict[str, Path]
    missing_files: tuple[str, ...]
    reason: str | None = None
    package_version: str | None = None

    def resource_route(self, resource_name: str, relative_path: str | None = None) -> str | None:
        if resource_name not in self.resource_dirs:
            return None

        route = f"/runtime/packages/{self.definition.id}/resources/{resource_name}"
        if not relative_path:
            return route

        normalized = relative_path.replace("\\", "/").strip("/")
        if not normalized:
            return route
        return f"{route}/{normalized}"

    def to_payload(self, base_url: str | None = None) -> dict[str, Any]:
        resources = {
            key: str(path)
            for key, path in self.resource_dirs.items()
        }
        resource_urls = {}
        if base_url:
            resource_urls = {
                key: f"{base_url}{self.resource_route(key)}"
                for key in self.resource_dirs.keys()
            }

        return {
            "id": self.definition.id,
            "displayName": self.definition.display_name,
            "type": self.definition.package_type,
            "version": self.definition.version,
            "packageVersion": self.package_version or self.definition.version,
            "minHostVersion": self.definition.min_host_version,
            "minPackageVersion": self.definition.min_package_version,
            "installDir": str(self.root_dir) if self.root_dir else None,
            "entryExecutable": str(self.entry_executable) if self.entry_executable else None,
            "entryArguments": list(self.entry_arguments),
            "healthEndpoint": self.definition.health_endpoint,
            "autoStart": self.definition.auto_start,
            "optional": self.definition.optional,
            "capabilities": list(self.definition.capabilities),
            "state": self.status,
            "source": self.source_name,
            "reason": self.reason,
            "missingFiles": list(self.missing_files),
            "resourceDirs": resources,
            "resourceUrls": resource_urls,
        }


class CapabilityPackageRegistry:
    def __init__(self, contract_path: Path | None = None):
        self._roots = _runtime_roots()
        default_contract_path = (
            BASE_DIR / "config" / "capability-packages.json"
            if IS_FROZEN
            else self._roots["project"] / "config" / "capability-packages.json"
        )
        self._contract_path = contract_path or default_contract_path
        self._host_version = "0.0.0"
        self._definitions = self._load_definitions()

    @property
    def host_version(self) -> str:
        return self._host_version

    def list_packages(self) -> list[CapabilityPackageDefinition]:
        return list(self._definitions.values())

    def get_definition(self, package_id: str) -> CapabilityPackageDefinition | None:
        return self._definitions.get(package_id)

    def package_for_capability(self, capability: str) -> CapabilityPackageDefinition | None:
        for definition in self._definitions.values():
            if capability in definition.capabilities:
                return definition
        return None

    def resolve(self, package_id: str) -> ResolvedCapabilityPackage | None:
        definition = self.get_definition(package_id)
        if not definition:
            return None
        return self._resolve_definition(definition)

    def list_snapshots(self, base_url: str | None = None) -> list[dict[str, Any]]:
        payload: list[dict[str, Any]] = []
        for definition in self._definitions.values():
            snapshot = self._resolve_definition(definition)
            payload.append(snapshot.to_payload(base_url))
        return payload

    def get_snapshot(self, package_id: str, base_url: str | None = None) -> dict[str, Any] | None:
        snapshot = self.resolve(package_id)
        if not snapshot:
            return None
        return snapshot.to_payload(base_url)

    def should_auto_start(self, capability: str) -> bool:
        definition = self.package_for_capability(capability)
        if not definition or not definition.auto_start:
            return False
        snapshot = self._resolve_definition(definition)
        return snapshot.status == STATUS_READY and snapshot.entry_executable is not None

    def static_mounts(self) -> list[tuple[str, Path]]:
        mounts: list[tuple[str, Path]] = []
        for definition in self._definitions.values():
            snapshot = self._resolve_definition(definition)
            if snapshot.status != STATUS_READY:
                continue
            for name, path in snapshot.resource_dirs.items():
                mounts.append((f"/runtime/packages/{definition.id}/resources/{name}", path))
        return mounts

    def _load_definitions(self) -> dict[str, CapabilityPackageDefinition]:
        raw = json.loads(self._contract_path.read_text(encoding="utf-8"))
        self._host_version = str(raw.get("hostVersion") or "0.0.0")
        definitions: dict[str, CapabilityPackageDefinition] = {}

        for item in raw.get("packages", []):
            sources = tuple(
                CapabilityPackageSource(
                    name=str(source["name"]),
                    root=str(source["root"]),
                    entry_executable=source.get("entryExecutable"),
                    entry_arguments=tuple(source.get("entryArguments") or []),
                    required_files=tuple(source.get("requiredFiles") or []),
                    resource_dirs=dict(source.get("resourceDirs") or {}),
                )
                for source in item.get("sources", [])
            )
            definition = CapabilityPackageDefinition(
                id=str(item["id"]),
                version=str(item["version"]),
                min_host_version=str(item.get("minHostVersion") or "0.0.0"),
                min_package_version=str(item.get("minPackageVersion") or item["version"]),
                install_dir=str(item["installDir"]),
                package_type=str(item.get("type") or "runtime"),
                entry_executable=item.get("entryExecutable"),
                entry_arguments=tuple(item.get("entryArguments") or []),
                health_endpoint=item.get("healthEndpoint"),
                required_files=tuple(item.get("requiredFiles") or []),
                resource_dirs=dict(item.get("resourceDirs") or {}),
                platform=tuple(item.get("platform") or []),
                arch=tuple(item.get("arch") or []),
                auto_start=bool(item.get("autoStart")),
                optional=bool(item.get("optional", True)),
                display_name=str(item.get("displayName") or item["id"]),
                failure_mode=str(item.get("failureMode") or "unavailable"),
                capabilities=tuple(item.get("capabilities") or []),
                sources=sources,
            )
            definitions[definition.id] = definition

        return definitions

    def _resolve_definition(self, definition: CapabilityPackageDefinition) -> ResolvedCapabilityPackage:
        platform_ok = not definition.platform or sys.platform in definition.platform
        current_arch = _normalize_arch(os.environ.get("PROCESSOR_ARCHITECTURE") or platform.machine())
        arch_ok = not definition.arch or current_arch in {
            _normalize_arch(value) for value in definition.arch
        }

        if not platform_ok or not arch_ok:
            return ResolvedCapabilityPackage(
                definition=definition,
                status=STATUS_UNAVAILABLE,
                source_name=None,
                root_dir=None,
                entry_executable=None,
                entry_arguments=(),
                resource_dirs={},
                missing_files=(),
                reason="platform-mismatch",
            )

        if not _version_gte(self.host_version, definition.min_host_version):
            return ResolvedCapabilityPackage(
                definition=definition,
                status=STATUS_FAILED,
                source_name=None,
                root_dir=None,
                entry_executable=None,
                entry_arguments=(),
                resource_dirs={},
                missing_files=(),
                reason="host-version-too-old",
            )

        candidates = list(definition.sources) or [
            CapabilityPackageSource(
                name="installed",
                root=definition.install_dir,
                entry_executable=definition.entry_executable,
                entry_arguments=definition.entry_arguments,
                required_files=definition.required_files,
                resource_dirs=definition.resource_dirs,
            )
        ]

        first_failure: tuple[str, tuple[str, ...]] | None = None
        for candidate in candidates:
            root_dir = _expand_path(candidate.root, self._roots)
            if root_dir is None:
                continue

            required_files = candidate.required_files or definition.required_files
            missing_files = tuple(
                item for item in required_files if not (root_dir / item).exists()
            )
            if missing_files:
                if first_failure is None:
                    first_failure = (candidate.name, missing_files)
                continue

            resource_map = candidate.resource_dirs or definition.resource_dirs
            resolved_resources = {
                key: (root_dir / relative_path).resolve()
                for key, relative_path in resource_map.items()
                if (root_dir / relative_path).exists()
            }
            entry_relative = candidate.entry_executable or definition.entry_executable
            entry_executable = (root_dir / entry_relative).resolve() if entry_relative else None
            if entry_relative and entry_executable and not entry_executable.exists():
                if first_failure is None:
                    first_failure = (candidate.name, (entry_relative,))
                continue

            package_version = self._read_package_version(root_dir)
            if package_version and not _version_gte(package_version, definition.min_package_version):
                return ResolvedCapabilityPackage(
                    definition=definition,
                    status=STATUS_FAILED,
                    source_name=candidate.name,
                    root_dir=root_dir,
                    entry_executable=None,
                    entry_arguments=(),
                    resource_dirs={},
                    missing_files=(),
                    reason="package-version-too-old",
                    package_version=package_version,
                )

            return ResolvedCapabilityPackage(
                definition=definition,
                status=STATUS_READY,
                source_name=candidate.name,
                root_dir=root_dir,
                entry_executable=entry_executable,
                entry_arguments=candidate.entry_arguments or definition.entry_arguments,
                resource_dirs=resolved_resources,
                missing_files=(),
                reason=None,
                package_version=package_version,
            )

        return ResolvedCapabilityPackage(
            definition=definition,
            status=STATUS_UNAVAILABLE,
            source_name=first_failure[0] if first_failure else None,
            root_dir=None,
            entry_executable=None,
            entry_arguments=(),
            resource_dirs={},
            missing_files=first_failure[1] if first_failure else (),
            reason="missing-package",
        )

    @staticmethod
    def _read_package_version(root_dir: Path) -> str | None:
        version_path = root_dir / "version.json"
        if not version_path.exists():
            return None
        try:
            raw = json.loads(version_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return str(raw.get("version") or raw.get("packageVersion") or "")
