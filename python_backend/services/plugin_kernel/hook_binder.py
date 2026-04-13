from __future__ import annotations

from core.interfaces.plugin import Plugin


class HookBinder:
    def __init__(self):
        self._hooked_plugins: set[str] = set()

    def register(self, plugin: Plugin) -> None:
        if plugin.id in self._hooked_plugins:
            return

        from sdk.lumina.hook import HookManager

        hook_manager = HookManager.instance()
        if not hook_manager:
            return

        for attr_name in dir(plugin):
            handler = getattr(plugin, attr_name)
            hook_info = getattr(handler, "_hook_info", None)
            if not hook_info:
                continue

            hook_manager.register(
                hook_name=hook_info["name"],
                handler=handler,
                plugin_id=plugin.id,
                priority=hook_info.get("priority", 50),
                after=hook_info.get("after", []),
                before=hook_info.get("before", []),
            )

        self._hooked_plugins.add(plugin.id)

    def unregister(self, plugin_id: str) -> None:
        from sdk.lumina.hook import HookManager

        hook_manager = HookManager.instance()
        if hook_manager and plugin_id in self._hooked_plugins:
            hook_manager.unregister(plugin_id)
        self._hooked_plugins.discard(plugin_id)
