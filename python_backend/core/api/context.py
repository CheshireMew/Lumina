import logging
from pathlib import Path
from typing import Any

from core.events import EventBus
from core.services.service_registry import get_service_registry, ServiceRegistry
from core.utils.frozen_proxy import FrozenProxy

logger = logging.getLogger("LuminaContext")


class LuminaContext:
    """
    Unified capability module context.

    Internal capabilities may interact with:
    - events
    - capability discovery
    - scoped config
    - scoped data
    """

    def __init__(
        self,
        container: Any,
        module_id: str,
        manifest: Any,
        event_bus: EventBus,
        capability_registry: Any,
        service_registry: ServiceRegistry | None = None,
    ):
        if container is None:
            raise ValueError("LuminaContext requires ServiceContainer")
        if event_bus is None:
            raise ValueError("LuminaContext requires EventBus")
        if capability_registry is None:
            raise ValueError("LuminaContext requires CapabilityRegistry")

        self.module_id = module_id
        self.manifest = manifest
        self._container = container
        self._capability_registry = capability_registry
        self._service_registry = service_registry or get_service_registry()
        self.events = event_bus
        self.config = FrozenProxy(container.get_config())

    def get_logger(self, name: str):
        return logging.getLogger(name)

    def get_config(self) -> dict[str, Any]:
        provider_settings = getattr(self._container.get_config().capabilities, "settings", {})
        return dict(provider_settings.get(self.module_id, {}))

    def update_config(self, key: str, value: Any):
        config = self._container.get_config()
        settings = config.capabilities.settings.setdefault(self.module_id, {})
        settings[key] = value
        config.save()

    def load_data(self) -> dict[str, Any]:
        soul = self._container.get_soul()
        return soul.load_module_data(self.module_id)

    def save_data(self, data: dict[str, Any]):
        soul = self._container.get_soul()
        soul.save_module_data(self.module_id, data)

    def get_data_dir(self) -> Path | None:
        soul = self._container.get_soul()
        return soul.get_module_data_dir(self.module_id)

    async def emit(self, event_type: str, payload: Any = None):
        await self.events.emit(event_type, payload)

    def subscribe(self, event_type: str, handler: Any):
        self.events.subscribe(event_type, handler)

    def find_capability(self, capability: str, runtime_target: str | None = None) -> str | None:
        return self._capability_registry.find_provider(
            capability,
            runtime_target=runtime_target,
            only_enabled=True,
        )

    def get_service(self, name: str) -> Any:
        service = self._service_registry.resolve(name, container=self._container)
        if service is None:
            raise AttributeError(f"Unknown service: {name}")
        return service

    def __getattr__(self, name: str):
        if name.startswith("_"):
            raise AttributeError(name)
        raise AttributeError(
            f"'{name}' is not a public capability context API. "
            "Use events, get_config(), update_config(), load_data(), save_data(), get_data_dir(), find_capability(), get_service()."
        )
