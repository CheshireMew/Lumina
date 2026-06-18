from __future__ import annotations

from typing import Any, Dict, Optional

from core.runtime import (
    MAIN_RUNTIME_TARGET,
    get_capability_contract,
    normalize_runtime_target,
    runtime_target_to_worker_id,
)
from security.tokens import TokenManager
from services.infra.service_discovery import discovery


class RuntimeService:
    def __init__(self, container):
        self.container = container

    def get_capability_runtime(self, capability: str, base_url: str) -> dict[str, Any]:
        contract = get_capability_contract(capability)
        config = self.container.get_config()
        selected_provider = config.get_selected_provider(capability)
        provider_state: dict[str, Any] = {}
        current_provider = selected_provider

        runtime_target = normalize_runtime_target(
            contract.worker_runtime_target if contract else MAIN_RUNTIME_TARGET
        )
        worker_id = runtime_target_to_worker_id(runtime_target)
        worker_node = discovery.get_node(worker_id)
        process_manager = self.container.get_process_manager()
        worker_online = (
            worker_node is not None
            or runtime_target == MAIN_RUNTIME_TARGET
            or process_manager.is_running(worker_id)
        )

        direct_base_url: Optional[str]
        try:
            direct_base_url = discovery.get_url(runtime_target)
        except Exception:
            try:
                direct_base_url = config.network.get_worker_url(runtime_target)
            except Exception:
                direct_base_url = None

        stream_url = None
        token = None
        if contract and direct_base_url and contract.stream_routes.get("audio"):
            token = TokenManager.create_token(
                worker_id,
                scopes=["audio.stream", f"capability.{capability}"],
                ttl_minutes=10,
                scope="worker_access",
            )
            stream_url = f"ws://127.0.0.1:{direct_base_url.rsplit(':', 1)[1]}{contract.stream_routes['audio']}?token={token}"
            if direct_base_url.startswith("http://"):
                stream_url = direct_base_url.replace("http://", "ws://", 1) + f"{contract.stream_routes['audio']}?token={token}"

        return {
            "capability": capability,
            "contract_version": contract.version if contract else "1.0",
            "supported_operations": list(contract.supported_operations) if contract else [],
            "selected_provider": selected_provider,
            "current_provider": current_provider,
            "runtime_target": runtime_target,
            "worker_id": worker_id,
            "worker_online": worker_online,
            "control_base_url": f"{base_url}/{capability}",
            "direct_base_url": direct_base_url,
            "stream_url": stream_url,
            "token": token,
            "last_error": provider_state.get("error"),
            "load_time_ms": provider_state.get("load_time_ms"),
            "status": "ready" if worker_online else "offline",
            "provider_state": provider_state,
        }


def get_runtime_service(container) -> RuntimeService:
    return RuntimeService(container)
