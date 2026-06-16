from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable


PluginState = dict[str, Any]
StateProvider = Callable[[], list[PluginState] | Awaitable[list[PluginState]]]


async def _resolve_states(provider: StateProvider | None) -> list[PluginState]:
    if provider is None:
        return []

    result = provider()
    if inspect.isawaitable(result):
        result = await result

    if not isinstance(result, list):
        return []

    return [item for item in result if isinstance(item, dict)]


def build_runtime_state_provider(
    capability_provider: StateProvider | None,
    *,
    container,
) -> Callable[[], Awaitable[list[PluginState]]]:
    async def provide() -> list[PluginState]:
        merged: dict[str, PluginState] = {}

        for item in await _resolve_states(capability_provider):
            plugin_id = item.get("id")
            if plugin_id:
                merged[plugin_id] = dict(item)

        plugin_manager = container.get_system_plugin_manager()
        if plugin_manager:
            for item in plugin_manager.list_plugins():
                plugin_id = item.get("id")
                if not plugin_id:
                    continue
                merged[plugin_id] = {**merged.get(plugin_id, {}), **item}

        return list(merged.values())

    return provide
