from __future__ import annotations

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


MAIN_RUNTIME_TARGET = "main"
WORKER_RUNTIME_PREFIX = "worker:"


@dataclass(frozen=True)
class CapabilityContractDefinition:
    capability: str
    version: str
    runtime_id: str | None
    worker_runtime_target: str
    port_key: str
    control_base_path: str
    provider_backed: bool
    worker_routes: dict[str, str] = field(default_factory=dict)
    stream_routes: dict[str, str] = field(default_factory=dict)
    supported_operations: tuple[str, ...] = ()


def _runtime_catalog_path() -> Path:
    candidates: list[Path] = []
    app_root = os.environ.get("LUMINA_APP_ROOT")
    if app_root:
        candidates.append(Path(app_root) / "config" / "worker-runtimes.json")
    candidates.append(Path(__file__).resolve().parents[2] / "config" / "worker-runtimes.json")
    candidates.append(Path(__file__).resolve().parents[1] / "config" / "worker-runtimes.json")
    path = next((candidate for candidate in candidates if candidate.exists()), None)
    if path is None:
        searched = ", ".join(str(candidate) for candidate in candidates)
        raise FileNotFoundError(f"config/worker-runtimes.json not found. Searched: {searched}")
    return path


def _load_capability_contracts() -> dict[str, CapabilityContractDefinition]:
    raw = json.loads(_runtime_catalog_path().read_text(encoding="utf-8-sig"))
    contracts: dict[str, CapabilityContractDefinition] = {}
    runtime_port_keys: dict[str, str] = {}
    for item in raw.get("capabilityContracts", []):
        capability = str(item["capability"])
        if capability in contracts:
            raise ValueError(f"Duplicate capability contract: {capability}")
        runtime_target = str(item["runtimeTarget"])
        port_key = str(item["portKey"])
        existing_port_key = runtime_port_keys.setdefault(runtime_target, port_key)
        if existing_port_key != port_key:
            raise ValueError(
                f"Runtime target '{runtime_target}' has conflicting port keys: "
                f"{existing_port_key}, {port_key}"
            )
        contracts[capability] = CapabilityContractDefinition(
            capability=capability,
            version=str(item["version"]),
            runtime_id=item.get("runtimeId"),
            worker_runtime_target=runtime_target,
            port_key=port_key,
            control_base_path=str(item["controlBasePath"]),
            provider_backed=bool(item.get("providerBacked", True)),
            worker_routes=dict(item.get("workerRoutes") or {}),
            stream_routes=dict(item.get("streamRoutes") or {}),
            supported_operations=tuple(item.get("supportedOperations") or []),
        )
    if not contracts:
        raise ValueError("Runtime catalog defines no capability contracts")
    return contracts


CAPABILITY_CONTRACTS = _load_capability_contracts()


def normalize_runtime_target(value: str | None) -> str:
    if not value:
        return MAIN_RUNTIME_TARGET

    normalized = value.strip().lower()

    if normalized == MAIN_RUNTIME_TARGET:
        return MAIN_RUNTIME_TARGET

    if normalized.startswith(WORKER_RUNTIME_PREFIX):
        capability = normalized.split(":", 1)[1].strip()
        if capability:
            return f"{WORKER_RUNTIME_PREFIX}{capability}"

    return MAIN_RUNTIME_TARGET


def runtime_target_for_capability(capability: str) -> str:
    contract = CAPABILITY_CONTRACTS.get(capability)
    if contract:
        return contract.worker_runtime_target
    return MAIN_RUNTIME_TARGET


def runtime_target_to_worker_id(runtime_target: str) -> str:
    normalized = normalize_runtime_target(runtime_target)
    if normalized == MAIN_RUNTIME_TARGET:
        return MAIN_RUNTIME_TARGET
    return normalized


def runtime_target_to_capability(runtime_target: str) -> str | None:
    normalized = normalize_runtime_target(runtime_target)
    if normalized == MAIN_RUNTIME_TARGET:
        return None
    return normalized.split(":", 1)[1]


def worker_id_for_capability(capability: str) -> str:
    return runtime_target_to_worker_id(runtime_target_for_capability(capability))


def get_capability_contract(capability: str) -> CapabilityContractDefinition | None:
    return CAPABILITY_CONTRACTS.get(capability)


def list_capability_names() -> tuple[str, ...]:
    return tuple(CAPABILITY_CONTRACTS)


def list_capability_contracts() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for contract in CAPABILITY_CONTRACTS.values():
        payload.append(
            {
                "capability": contract.capability,
                "version": contract.version,
                "runtime_id": contract.runtime_id,
                "runtime_target": contract.worker_runtime_target,
                "port_key": contract.port_key,
                "control_base_path": contract.control_base_path,
                "provider_backed": contract.provider_backed,
                "worker_routes": dict(contract.worker_routes),
                "stream_routes": dict(contract.stream_routes),
                "supported_operations": list(contract.supported_operations),
            }
        )
    return payload


def port_key_for_runtime_target(runtime_target: str) -> str | None:
    normalized = normalize_runtime_target(runtime_target)
    port_keys = {
        contract.port_key
        for contract in CAPABILITY_CONTRACTS.values()
        if normalize_runtime_target(contract.worker_runtime_target) == normalized
    }
    if len(port_keys) > 1:
        raise ValueError(f"Runtime target '{normalized}' has multiple configured port keys")
    return next(iter(port_keys), None)


def resolve_runtime_host(config: Any, runtime_target: str) -> str | None:
    return config.network.runtime_host(runtime_target)


def resolve_runtime_base_url(config: Any, runtime_target: str) -> str | None:
    return config.network.runtime_base_url(runtime_target)


def resolve_capability_base_url(config: Any, capability: str) -> str | None:
    return resolve_runtime_base_url(config, runtime_target_for_capability(capability))


def resolve_contract_path(capability: str, operation: str) -> str | None:
    contract = get_capability_contract(capability)
    if not contract:
        return None
    return contract.worker_routes.get(operation)


def resolve_contract_url(config: Any, capability: str, operation: str) -> str | None:
    base_url = resolve_capability_base_url(config, capability)
    route = resolve_contract_path(capability, operation)
    if not base_url or not route:
        return None
    return f"{base_url}{route}"


def resolve_runtime_port(config: Any, runtime_target: str) -> int | None:
    return config.network.runtime_port(runtime_target)
