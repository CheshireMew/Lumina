from __future__ import annotations

from typing import Any

from core.api.context import LuminaContext
from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest


class PluginContextBinder:
    def __init__(self, container: Any, router_manager: Any, capability_registry: Any):
        self.container = container
        self.router_manager = router_manager
        self.capability_registry = capability_registry

    async def bind(self, plugin: Plugin, manifest: PluginManifest) -> None:
        context = LuminaContext(
            container=self.container,
            plugin_id=manifest.id,
            manifest=manifest,
            event_bus=getattr(self.container, "event_bus", None),
            router_manager=self.router_manager,
            capability_registry=self.capability_registry,
        )
        await plugin.load(context)
