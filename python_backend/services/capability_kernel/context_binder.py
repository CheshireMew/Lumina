from __future__ import annotations

from typing import Any

from core.api.context import LuminaContext
from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest


class CapabilityContextBinder:
    def __init__(self, container: Any, capability_registry: Any):
        if container is None:
            raise ValueError("CapabilityContextBinder requires ServiceContainer")
        if capability_registry is None:
            raise ValueError("CapabilityContextBinder requires CapabilityRegistry")

        self.container = container
        self.capability_registry = capability_registry

    async def bind(self, capability: CapabilityModule, manifest: CapabilityManifest) -> None:
        context = LuminaContext(
            container=self.container,
            module_id=manifest.id,
            manifest=manifest,
            event_bus=self.container.get_event_bus(),
            capability_registry=self.capability_registry,
        )
        await capability.load(context)
