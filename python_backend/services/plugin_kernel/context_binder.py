from __future__ import annotations

from typing import Any

from core.api.context import LuminaContext
from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest


class PluginContextBinder:
    def __init__(self, container: Any, capability_registry: Any):
        self.container = container
        self.capability_registry = capability_registry

    async def bind(self, plugin: Plugin, manifest: PluginManifest) -> None:
        context = LuminaContext(
            container=self.container,
            plugin_id=manifest.id,
            manifest=manifest,
            event_bus=(
                self.container.get_event_bus()
                if self.container.has_service("event_bus")
                else None
            ),
            capability_registry=self.capability_registry,
        )
        await plugin.load(context)
