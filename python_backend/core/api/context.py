import logging
from pathlib import Path
from typing import Any

from core.events import EventBus, get_event_bus
from core.services.service_registry import get_service_registry, ServiceRegistry
from core.utils.frozen_proxy import FrozenProxy

logger = logging.getLogger("PluginContext")


class LuminaContext:
    """
    Unified plugin context.

    Internal capabilities may interact with:
    - events
    - capability discovery
    - scoped config
    - scoped data
    """

    def __init__(
        self,
        container: Any,
        plugin_id: str,
        manifest: Any,
        event_bus: EventBus | None = None,
        capability_registry: Any = None,
        service_registry: ServiceRegistry | None = None,
    ):
        self.plugin_id = plugin_id
        self.manifest = manifest
        self._container = container
        self._capability_registry = capability_registry
        self._service_registry = service_registry or get_service_registry()
        self.events = event_bus or get_event_bus()
        self.config = FrozenProxy(container.get_config()) if container and container.has_service("config") else None

    def get_logger(self, name: str):
        return logging.getLogger(name)

    def get_config(self) -> dict[str, Any]:
        plugin_settings = getattr(self._container.get_config().plugins, "settings", {})
        return dict(plugin_settings.get(self.plugin_id, {}))

    def update_config(self, key: str, value: Any):
        config = self._container.get_config()
        settings = config.plugins.settings.setdefault(self.plugin_id, {})
        settings[key] = value
        config.save()

    def load_data(self) -> dict[str, Any]:
        soul = self._container.get_soul()
        if soul:
            return soul.load_module_data(self.plugin_id)
        return {}

    def save_data(self, data: dict[str, Any]):
        soul = self._container.get_soul()
        if soul:
            soul.save_module_data(self.plugin_id, data)

    def get_data_dir(self) -> Path | None:
        soul = self._container.get_soul()
        if soul:
            return soul.get_module_data_dir(self.plugin_id)
        return None

    async def emit(self, event_type: str, payload: Any = None):
        await self.events.emit(event_type, payload)

    def subscribe(self, event_type: str, handler: Any):
        self.events.subscribe(event_type, handler)

    def find_capability(self, capability: str, runtime_target: str | None = None) -> str | None:
        if not self._capability_registry:
            return None

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
            f"'{name}' is not a public plugin context API. "
            "Use events, get_config(), update_config(), load_data(), save_data(), get_data_dir(), find_capability(), get_service()."
        )
