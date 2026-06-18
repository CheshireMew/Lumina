from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Optional

logger = logging.getLogger("ServiceRegistry")


CONTAINER_SERVICE_GETTERS = {
    "automation_service": "get_automation_service",
    "worker_runtime_registry": "get_worker_runtime_registry",
    "character_service": "get_character_service",
    "chat_pipeline": "get_chat_pipeline",
    "chat_turn_event_adapter": "get_chat_turn_event_adapter",
    "chat_turn_service": "get_chat_turn_service",
    "companion_runtime": "get_companion_runtime",
    "companion_context_resolver": "get_companion_context_resolver",
    "companion_interaction_recorder": "get_companion_interaction_recorder",
    "config": "get_config",
    "config_watcher": "get_config_watcher",
    "event_bus": "get_event_bus",
    "gateway": "get_gateway",
    "llm_manager": "get_llm_manager",
    "memory": "get_memory",
    "provider_config_service": "get_provider_config_service",
    "prewarm_task": "get_prewarm_task",
    "process_manager": "get_process_manager",
    "session_manager": "get_session_manager",
    "skill_manager": "get_skill_manager",
    "soul": "get_soul",
    "stt": "get_stt",
    "ticker": "get_ticker",
    "tts": "get_tts",
    "vision": "get_vision",
}


class ServiceRegistry:
    """
    Local service registry for route code and explicit services.

    The registry resolves services from two places:
    - explicit registrations
    - the process container

    This keeps service lookup out of EventBus and gives the project a single
    local service resolution entry point.
    """

    _instance: Optional["ServiceRegistry"] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._lock = RLock()
        self._overrides: dict[str, Any] = {}

    def register(self, name: str, instance: Any) -> None:
        with self._lock:
            self._overrides[name] = instance

    def unregister(self, name: str) -> bool:
        with self._lock:
            if name not in self._overrides:
                return False
            del self._overrides[name]
            return True

    def resolve(self, name: str, container: Any = None) -> Any:
        with self._lock:
            if name in self._overrides:
                return self._overrides[name]

        container = container or self._default_container()
        if not container:
            return None

        return self._resolve_from_container(container, name)

    def list_services(self, container: Any = None) -> list[str]:
        names = set(self._overrides.keys())
        container = container or self._default_container()
        if container:
            names.update(self._list_container_services(container))
        return sorted(names)

    def _default_container(self) -> Any:
        try:
            from services.container import services

            return services
        except Exception:
            return None

    def _resolve_from_container(self, container: Any, name: str) -> Any:
        getter_name = CONTAINER_SERVICE_GETTERS.get(name)
        if not getter_name:
            return None

        getter = getattr(container, getter_name)
        try:
            resolved = getter()
        except Exception as exc:
            logger.debug("Failed to resolve %s from container via %s: %s", name, getter_name, exc)
            return None

        if resolved is not None:
            return resolved
        return None

    def _list_container_services(self, container: Any) -> list[str]:
        return sorted(
            name
            for name in CONTAINER_SERVICE_GETTERS
            if self._resolve_from_container(container, name) is not None
        )


def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry()
