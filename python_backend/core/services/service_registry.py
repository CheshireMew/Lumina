from __future__ import annotations

import logging
from threading import RLock
from typing import Any, Optional

logger = logging.getLogger("ServiceRegistry")


class ServiceRegistry:
    """
    Local service registry for plugin and route code.

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
        candidates = [f"get_{name}", name]
        for candidate in candidates:
            if not hasattr(container, candidate):
                continue

            value = getattr(container, candidate)
            try:
                resolved = value() if callable(value) else value
            except Exception as exc:
                logger.debug("Failed to resolve %s from container via %s: %s", name, candidate, exc)
                continue

            if resolved is not None:
                return resolved
        return None

    def _list_container_services(self, container: Any) -> list[str]:
        names: set[str] = set()
        for attr in dir(container):
            if attr.startswith("_"):
                continue
            if attr.startswith("get_"):
                names.add(attr[4:])
                continue

            value = getattr(container, attr, None)
            if callable(value):
                continue
            names.add(attr)
        return sorted(names)


def get_service_registry() -> ServiceRegistry:
    return ServiceRegistry()
