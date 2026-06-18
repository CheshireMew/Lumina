from __future__ import annotations

import inspect
from typing import Any, Awaitable, Callable


RuntimeState = dict[str, Any]
StateProvider = Callable[[], list[RuntimeState] | Awaitable[list[RuntimeState]]]


async def _resolve_states(provider: StateProvider | None) -> list[RuntimeState]:
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
) -> Callable[[], Awaitable[list[RuntimeState]]]:
    async def provide() -> list[RuntimeState]:
        merged: dict[str, RuntimeState] = {}

        for item in await _resolve_states(capability_provider):
            state_id = item.get("id")
            if state_id:
                merged[state_id] = dict(item)

        return list(merged.values())

    return provide
