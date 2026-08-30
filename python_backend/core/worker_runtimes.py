from __future__ import annotations

import json
import os
import platform
import sys
from dataclasses import dataclass, field
from pathlib import Path

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
class WorkerRuntimeSource:
    name: str
    root: str
    entry_executable: str | None = None
    entry_arguments: tuple[str, ...] = ()
    required_files: tuple[str, ...] = ()
    resource_dirs: dict[str, str] = field(default_factory=dict)


@dataclass(frozen=True)
class WorkerRuntimeDefinition:
    id: str
    version: str
    min_host_version: str
    min_runtime_version: str
    install_dir: str
    runtime_type: str
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
    sources: tuple[WorkerRuntimeSource, ...] = ()


@dataclass(frozen=True)
class ResolvedWorkerRuntime:
    definition: WorkerRuntimeDefinition
    status: str
    source_name: str | None
    root_dir: Path | None
    entry_executable: Path | None
    entry_arguments: tuple[str, ...]
    missing_files: tuple[str, ...]
    reason: str | None = None
    runtime_version: str | None = None


class WorkerRuntimeRegistry:
    def __init__(self, contract_path: Path | None = None):
        self._roots = _runtime_roots()
        default_contract_path = (
            BASE_DIR / "config" / "worker-runtimes.json"
            if IS_FROZEN
            else self._roots["project"] / "config" / "worker-runtimes.json"
        )
        self._contract_path = contract_path or default_contract_path
        self._host_version = "0.0.0"
        self._definitions = self._load_definitions()
        self._validate_capability_contracts()

    @property
    def host_version(self) -> str:
        return self._host_version

    def list_runtimes(self) -> list[WorkerRuntimeDefinition]:
        return list(self._definitions.values())

    def get_definition(self, runtime_id: str) -> WorkerRuntimeDefinition | None:
        return self._definitions.get(runtime_id)

    def runtime_for_capability(self, capability: str) -> WorkerRuntimeDefinition | None:
        for definition in self._definitions.values():
            if capability in definition.capabilities:
                return definition
        return None

    def resolve(self, runtime_id: str) -> ResolvedWorkerRuntime | None:
        definition = self.get_definition(runtime_id)
        if not definition:
            return None
        return self._resolve_definition(definition)

    def should_auto_start(self, capability: str) -> bool:
        definition = self.runtime_for_capability(capability)
        if not definition or not definition.auto_start:
            return False
        snapshot = self._resolve_definition(definition)
        return snapshot.status == STATUS_READY and snapshot.entry_executable is not None

    def list_worker_capabilities(self) -> tuple[str, ...]:
        return tuple(
            capability
            for definition in self._definitions.values()
            if definition.runtime_type == "runtime"
            for capability in definition.capabilities
        )

    def list_auto_start_capabilities(self) -> tuple[str, ...]:
        return tuple(
            capability
            for definition in self._definitions.values()
            if definition.runtime_type == "runtime" and definition.auto_start
            for capability in definition.capabilities
        )

    def _validate_capability_contracts(self) -> None:
        from core.runtime import list_capability_contracts

        for contract in list_capability_contracts():
            runtime_id = contract["runtime_id"]
            if not runtime_id:
                continue
            definition = self._definitions.get(runtime_id)
            if definition is None:
                raise ValueError(
                    f"Capability '{contract['capability']}' references unknown runtime '{runtime_id}'"
                )
            if contract["capability"] not in definition.capabilities:
                raise ValueError(
                    f"Runtime '{runtime_id}' does not declare capability "
                    f"'{contract['capability']}'"
                )

    def _load_definitions(self) -> dict[str, WorkerRuntimeDefinition]:
        raw = json.loads(self._contract_path.read_text(encoding="utf-8"))
        self._host_version = str(raw.get("hostVersion") or "0.0.0")
        definitions: dict[str, WorkerRuntimeDefinition] = {}

        for item in raw.get("runtimes", []):
            sources = tuple(
                WorkerRuntimeSource(
                    name=str(source["name"]),
                    root=str(source["root"]),
                    entry_executable=source.get("entryExecutable"),
                    entry_arguments=tuple(source.get("entryArguments") or []),
                    required_files=tuple(source.get("requiredFiles") or []),
                    resource_dirs=dict(source.get("resourceDirs") or {}),
                )
                for source in item.get("sources", [])
            )
            definition = WorkerRuntimeDefinition(
                id=str(item["id"]),
                version=str(item["version"]),
                min_host_version=str(item.get("minHostVersion") or "0.0.0"),
                min_runtime_version=str(item.get("minRuntimeVersion") or item["version"]),
                install_dir=str(item["installDir"]),
                runtime_type=str(item.get("type") or "runtime"),
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

    def _resolve_definition(self, definition: WorkerRuntimeDefinition) -> ResolvedWorkerRuntime:
        platform_ok = not definition.platform or sys.platform in definition.platform
        current_arch = _normalize_arch(os.environ.get("PROCESSOR_ARCHITECTURE") or platform.machine())
        arch_ok = not definition.arch or current_arch in {
            _normalize_arch(value) for value in definition.arch
        }

        if not platform_ok or not arch_ok:
            return ResolvedWorkerRuntime(
                definition=definition,
                status=STATUS_UNAVAILABLE,
                source_name=None,
                root_dir=None,
                entry_executable=None,
                entry_arguments=(),
                missing_files=(),
                reason="platform-mismatch",
            )

        if not _version_gte(self.host_version, definition.min_host_version):
            return ResolvedWorkerRuntime(
                definition=definition,
                status=STATUS_FAILED,
                source_name=None,
                root_dir=None,
                entry_executable=None,
                entry_arguments=(),
                missing_files=(),
                reason="host-version-too-old",
            )

        candidates = list(definition.sources) or [
            WorkerRuntimeSource(
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

            entry_relative = candidate.entry_executable or definition.entry_executable
            if definition.runtime_type == "runtime" and not entry_relative:
                if first_failure is None:
                    first_failure = (candidate.name, ("<entryExecutable>",))
                continue
            entry_executable = (root_dir / entry_relative).resolve() if entry_relative else None
            if entry_relative and entry_executable and not entry_executable.exists():
                if first_failure is None:
                    first_failure = (candidate.name, (entry_relative,))
                continue

            runtime_version = self._read_runtime_version(root_dir)
            if runtime_version and not _version_gte(runtime_version, definition.min_runtime_version):
                return ResolvedWorkerRuntime(
                    definition=definition,
                    status=STATUS_FAILED,
                    source_name=candidate.name,
                    root_dir=root_dir,
                    entry_executable=None,
                    entry_arguments=(),
                    missing_files=(),
                    reason="runtime-version-too-old",
                    runtime_version=runtime_version,
                )

            return ResolvedWorkerRuntime(
                definition=definition,
                status=STATUS_READY,
                source_name=candidate.name,
                root_dir=root_dir,
                entry_executable=entry_executable,
                entry_arguments=candidate.entry_arguments or definition.entry_arguments,
                missing_files=(),
                reason=None,
                runtime_version=runtime_version,
            )

        return ResolvedWorkerRuntime(
            definition=definition,
            status=STATUS_UNAVAILABLE,
            source_name=first_failure[0] if first_failure else None,
            root_dir=None,
            entry_executable=None,
            entry_arguments=(),
            missing_files=first_failure[1] if first_failure else (),
            reason="missing-runtime",
        )

    @staticmethod
    def _read_runtime_version(root_dir: Path) -> str | None:
        version_path = root_dir / "version.json"
        if not version_path.exists():
            return None
        try:
            raw = json.loads(version_path.read_text(encoding="utf-8"))
        except Exception:
            return None
        return str(raw.get("version") or raw.get("runtimeVersion") or "")
