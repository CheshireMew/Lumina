from __future__ import annotations

from typing import Any, Dict, Optional

from core.runtime import (
    MAIN_RUNTIME_TARGET,
    get_capability_contract,
    normalize_runtime_target,
    runtime_target_to_worker_id,
)
from security.tokens import TokenManager


class RuntimeService:
    def __init__(
        self,
        *,
        config,
        worker_control_hub,
        worker_discovery,
        process_manager,
        worker_runtime_registry,
        llm_manager,
        memory_service,
    ):
        self.config = config
        self.worker_control_hub = worker_control_hub
        self.worker_discovery = worker_discovery
        self.process_manager = process_manager
        self.worker_runtime_registry = worker_runtime_registry
        self.llm_manager = llm_manager
        self.memory_service = memory_service

    def _control_base_url(self, capability: str, base_url: str) -> str:
        contract = get_capability_contract(capability)
        if not contract:
            return f"{base_url}/runtime/capabilities/{capability}"
        return f"{base_url}{contract.control_base_path}"

    def _provider_runtime_state(self, worker_id: str, capability: str, selected_provider: str | None) -> dict[str, Any]:
        try:
            worker = self.worker_control_hub.get_worker(worker_id)
        except Exception:
            worker = None

        if worker is None:
            return {}

        providers = [item for item in worker.providers if isinstance(item, dict)]
        exact = next((item for item in providers if item.get("id") == selected_provider), None)
        if exact is not None:
            return dict(exact)
        fallback = next(
            (
                item
                for item in providers
                if item.get("category") == capability and item.get("active_in_group")
            ),
            None,
        )
        return dict(fallback) if fallback is not None else {}

    @staticmethod
    def _capability_status(worker_online: bool, runtime_target: str, provider_state: dict[str, Any]) -> str:
        if not worker_online:
            return "offline"
        if not provider_state:
            return "starting"

        provider_status = provider_state.get("computed_status") or provider_state.get("status")
        if provider_status in {"ready", "running", "healthy", "idle"}:
            return "ready"
        if provider_status in {"error", "stuck"} or provider_state.get("error"):
            return "failed"
        return "unavailable"

    def _main_provider_state(
        self,
        capability: str,
        selected_provider: str | None,
    ) -> dict[str, Any]:
        if not selected_provider:
            return {"status": "error", "error": "No provider selected"}

        if capability == "llm":
            return self.llm_manager.get_runtime_provider_state(
                "chat",
                selected_provider,
            )

        if capability == "memory":
            return self.memory_service.get_runtime_provider_state(selected_provider)

        return {"status": "error", "error": f"Unsupported main capability: {capability}"}

    def get_capability_runtime(self, capability: str, base_url: str) -> dict[str, Any]:
        contract = get_capability_contract(capability)
        config = self.config
        selected_provider = (
            config.get_selected_provider(capability)
            if contract and contract.provider_backed
            else None
        )
        provider_state: dict[str, Any] = {}
        current_provider = selected_provider

        runtime_target = normalize_runtime_target(
            contract.worker_runtime_target if contract else MAIN_RUNTIME_TARGET
        )
        worker_id = runtime_target_to_worker_id(runtime_target)
        discovery = self.worker_discovery
        worker_node = discovery.get_node(worker_id)
        process_manager = self.process_manager
        if runtime_target == MAIN_RUNTIME_TARGET:
            if contract and contract.runtime_id:
                resource = self.worker_runtime_registry.resolve(contract.runtime_id)
                worker_online = bool(resource and resource.status == "ready")
                provider_state = {
                    "status": "ready" if worker_online else "error",
                    "error": None if worker_online else (
                        resource.reason if resource else "Runtime resource is not registered"
                    ),
                }
            else:
                worker_online = capability in {"llm", "memory"}
                provider_state = self._main_provider_state(capability, selected_provider)
        else:
            worker_online = worker_node is not None or process_manager.is_running(worker_id)
            provider_state = self._provider_runtime_state(
                worker_id,
                capability,
                selected_provider,
            )
            if provider_state.get("active_in_group"):
                current_provider = provider_state.get("id") or current_provider

        direct_base_url: Optional[str] = None
        if runtime_target == MAIN_RUNTIME_TARGET:
            direct_base_url = base_url
        elif worker_online:
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
            "runtime_id": contract.runtime_id if contract else None,
            "supported_operations": list(contract.supported_operations) if contract else [],
            "selected_provider": selected_provider,
            "current_provider": current_provider,
            "runtime_target": runtime_target,
            "worker_id": worker_id,
            "worker_online": worker_online,
            "control_base_url": self._control_base_url(capability, base_url),
            "direct_base_url": direct_base_url,
            "stream_url": stream_url,
            "token": token,
            "last_error": provider_state.get("error"),
            "load_time_ms": provider_state.get("load_time_ms"),
            "status": self._capability_status(worker_online, runtime_target, provider_state),
            "provider_state": provider_state,
        }
