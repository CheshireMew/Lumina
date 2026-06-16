from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any


MAIN_RUNTIME_TARGET = "main"
WORKER_RUNTIME_PREFIX = "worker:"


@dataclass(frozen=True)
class CapabilityContractDefinition:
    capability: str
    version: str
    worker_runtime_target: str
    worker_routes: dict[str, str] = field(default_factory=dict)
    stream_routes: dict[str, str] = field(default_factory=dict)
    supported_operations: tuple[str, ...] = ()


CAPABILITY_CONTRACTS: dict[str, CapabilityContractDefinition] = {
    "stt": CapabilityContractDefinition(
        capability="stt",
        version="1.0",
        worker_runtime_target="worker:stt",
        worker_routes={
            "models": "/models/list",
            "switch": "/models/switch",
            "audio_config": "/audio/config",
            "audio_devices": "/audio/devices",
            "voiceprint_status": "/voiceprint/status",
            "audio_status": "/audio/status",
            "health": "/health",
        },
        stream_routes={
            "audio": "/ws/stt",
        },
        supported_operations=(
            "models.list",
            "models.switch",
            "transcription.transcribe",
            "audio.config",
            "health.check",
        ),
    ),
    "tts": CapabilityContractDefinition(
        capability="tts",
        version="1.0",
        worker_runtime_target="worker:tts",
        worker_routes={
            "voices": "/voices",
            "synthesize": "/synthesize",
            "switch": "/models/switch",
            "models": "/models/list",
            "health": "/health",
        },
        supported_operations=(
            "voices.list",
            "speech.synthesize",
            "models.switch",
            "config.update",
            "health.check",
        ),
    ),
    "llm": CapabilityContractDefinition(
        capability="llm",
        version="1.0",
        worker_runtime_target="main",
        worker_routes={
            "chat": "/v1/chat/completions",
            "models": "/models/list",
            "health": "/health",
        },
        supported_operations=(
            "chat.generate",
            "tools.call",
            "models.list",
            "health.check",
        ),
    ),
    "memory": CapabilityContractDefinition(
        capability="memory",
        version="1.0",
        worker_runtime_target="main",
        worker_routes={
            "search": "/memory/search",
            "write": "/memory/add",
            "cleanup": "/memory/context/clear",
            "health": "/health",
        },
        supported_operations=(
            "memory.search",
            "memory.write",
            "memory.cleanup",
            "health.check",
        ),
    ),
    "vision": CapabilityContractDefinition(
        capability="vision",
        version="1.0",
        worker_runtime_target="worker:vision",
        worker_routes={
            "analyze": "/analyze",
            "load": "/load",
            "unload": "/unload",
            "health": "/health",
        },
        supported_operations=(
            "image.analyze",
            "models.load",
            "models.unload",
            "health.check",
        ),
    ),
}


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


def list_capability_contracts() -> list[dict[str, Any]]:
    payload: list[dict[str, Any]] = []
    for contract in CAPABILITY_CONTRACTS.values():
        payload.append(
            {
                "capability": contract.capability,
                "version": contract.version,
                "runtime_target": contract.worker_runtime_target,
                "worker_routes": dict(contract.worker_routes),
                "stream_routes": dict(contract.stream_routes),
                "supported_operations": list(contract.supported_operations),
            }
        )
    return payload


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
