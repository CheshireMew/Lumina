import logging
import inspect
from pathlib import Path
from typing import Any

from core.events.bus import bus
from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest, normalize_capability_id
from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target
from services.capability_registry import CapabilityRegistry
from services.plugin_kernel import (
    HookBinder,
    ManifestRepository,
    PermissionChecker,
    PluginContextBinder,
    PluginLoader,
    PluginPermissionError,
    PluginStateBuilder,
    is_selectable_provider,
)

logger = logging.getLogger("SystemPluginManager")


class SystemPluginManager:
    def __init__(self, container=None, router_manager=None, runtime_target: str = MAIN_RUNTIME_TARGET, base_dir: Path | None = None):
        self.container = container
        self.router_manager = router_manager
        self.event_bus = getattr(container, "event_bus", None) or bus
        self.runtime_target = normalize_runtime_target(runtime_target)
        self._plugin_root = Path(base_dir) if base_dir else Path(__file__).parent.parent / "plugins"
        self._plugins: dict[str, Plugin] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._errors: dict[str, str] = {}
        self._capability_registry = getattr(container, "capability_registry", None) or CapabilityRegistry()
        if container is not None:
            container.capability_registry = self._capability_registry
        self._manifest_repository = ManifestRepository(self._plugin_root)
        self._loader = PluginLoader()
        self._permission_checker = PermissionChecker()
        self._context_binder = PluginContextBinder(container, router_manager, self._capability_registry)
        self._hook_binder = HookBinder()
        self._state_builder = PluginStateBuilder(getattr(container, "config", None))
        self._lifecycle_subscriptions: list[int] = []

    @property
    def _config_service(self):
        from services.config_service import ConfigService

        return ConfigService(self.container)

    @property
    def plugins(self) -> dict[str, Plugin]:
        return self._plugins

    async def start(self):
        logger.info("Starting unified plugin kernel for runtime %s", self.runtime_target)
        self._subscribe_lifecycle_requests()
        self.refresh_manifests()

        for plugin_id, manifest in self._manifests.items():
            if not self.container.config.is_plugin_desired_enabled(plugin_id):
                continue
            await self._load_and_enable(plugin_id)

        await self._emit_all_states()
        logger.info("Unified plugin kernel ready")

    def _subscribe_lifecycle_requests(self):
        if self._lifecycle_subscriptions:
            return
        self._lifecycle_subscriptions.append(
            self.event_bus.subscribe("plugin.lifecycle.request_enable", self._on_enable_request)
        )
        self._lifecycle_subscriptions.append(
            self.event_bus.subscribe("plugin.lifecycle.request_disable", self._on_disable_request)
        )

    async def _on_enable_request(self, event):
        plugin_id = self._extract_plugin_id(event)
        if not plugin_id:
            return
        result = self.enable_plugin(plugin_id)
        if inspect.isawaitable(result):
            await result

    async def _on_disable_request(self, event):
        plugin_id = self._extract_plugin_id(event)
        if not plugin_id:
            return
        result = self.disable_plugin(plugin_id)
        if inspect.isawaitable(result):
            await result

    def _extract_plugin_id(self, event) -> str | None:
        payload = getattr(event, "data", event)
        if isinstance(payload, dict):
            return payload.get("plugin_id")
        return getattr(payload, "plugin_id", None)

    def refresh_manifests(self):
        previous_manifest_ids = set(self._manifests)
        retained_load_errors = {
            plugin_id: error
            for plugin_id, error in self._errors.items()
            if plugin_id in self._plugins
        }
        result = self._manifest_repository.discover(self.runtime_target)
        self._manifests = result.manifests
        self._errors = {**retained_load_errors, **result.errors}

        for plugin_id in previous_manifest_ids - set(self._manifests):
            self._capability_registry.unregister_plugin(plugin_id)

        for plugin_id, manifest in self._manifests.items():
            self._capability_registry.register_plugin(
                plugin_id=plugin_id,
                capabilities=manifest.all_capabilities(),
                runtime_target=manifest.runtime_target,
                kind=manifest.kind,
                enabled=bool(self._plugins.get(plugin_id) and self._plugins[plugin_id].enabled),
            )

    async def _load_and_enable(self, plugin_id: str) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            plugin = await self._instantiate_plugin(plugin_id)
            if plugin is None:
                return None
        await plugin.enable()
        self._hook_binder.register(plugin)
        self._capability_registry.set_enabled(plugin_id, True)
        await self._emit_state(plugin_id)
        return plugin

    async def _instantiate_plugin(self, plugin_id: str) -> Plugin | None:
        manifest = self._manifests.get(plugin_id)
        if manifest is None:
            return None

        try:
            self._permission_checker.ensure_allowed(manifest)
            plugin = self._loader.instantiate(manifest)
            await self._context_binder.bind(plugin, manifest)
            self._plugins[plugin_id] = plugin
            self._errors.pop(plugin_id, None)
            return plugin
        except PluginPermissionError:
            self._errors[plugin_id] = "permission_check_failed"
            return None
        except Exception as exc:
            logger.error("Failed to load plugin %s: %s", plugin_id, exc, exc_info=True)
            self._errors[plugin_id] = str(exc)
            return None

    def get_plugin(self, plugin_id: str) -> Plugin | None:
        return self._plugins.get(plugin_id)

    def get_manifest(self, plugin_id: str) -> PluginManifest | None:
        return self._manifests.get(plugin_id)

    def is_plugin_active(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        return bool(plugin and plugin.enabled)

    def find_provider(self, capability: str, runtime_target: str | None = None, **_: Any) -> str | None:
        normalized = normalize_capability_id(capability)
        selected = self.container.config.get_selected_provider(normalized)
        if selected is None and "." in normalized:
            selected = self.container.config.get_selected_provider(normalized.split(".")[0])
        return self._capability_registry.find_provider(
            capability=normalized,
            runtime_target=runtime_target,
            selected_provider=selected,
            only_enabled=True,
            predicate=lambda provider: provider.is_provider,
        )

    def list_plugins(self) -> list[dict[str, Any]]:
        return self._state_builder.build_all(self._manifests, self._plugins, self._errors)

    def list_manifest_errors(self) -> dict[str, str]:
        return dict(self._errors)

    async def enable_plugin(self, plugin_id: str) -> bool:
        manifest = self._manifests.get(plugin_id)
        if manifest is None:
            return False
        persist = not bool(getattr(self.container.config, "is_read_only", False))
        self._config_service.set_plugin_desired_state(plugin_id, True, persist=persist)
        plugin = await self._load_and_enable(plugin_id)
        if plugin and is_selectable_provider(manifest):
            self._config_service.set_selected_provider(manifest.capability, plugin_id, persist=persist)
        return plugin is not None

    async def disable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        manifest = self._manifests.get(plugin_id)
        persist = not bool(getattr(self.container.config, "is_read_only", False))
        self._config_service.set_plugin_desired_state(plugin_id, False, persist=persist)
        if manifest and is_selectable_provider(manifest):
            current_provider = self.container.config.get_selected_provider(manifest.capability)
            if current_provider == plugin_id:
                self._config_service.clear_selected_provider(manifest.capability, persist=persist)
        if plugin:
            self._hook_binder.unregister(plugin_id)
            await plugin.disable()
        self._capability_registry.set_enabled(plugin_id, False)
        await self._emit_state(plugin_id)
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        logger.warning("Hot reload is disabled in the unified kernel: %s", plugin_id)
        return False

    def get_active_ui_slots(self) -> list[dict[str, Any]]:
        return self._state_builder.active_ui_slots(self._plugins)

    async def shutdown(self):
        for sub_id in self._lifecycle_subscriptions:
            self.event_bus.unsubscribe(sub_id)
        self._lifecycle_subscriptions.clear()
        for plugin_id, plugin in list(self._plugins.items()):
            try:
                self._hook_binder.unregister(plugin_id)
                if plugin.enabled:
                    await plugin.disable()
                await plugin.unload()
            finally:
                self._capability_registry.set_enabled(plugin_id, False)

    def _build_state(self, plugin_id: str) -> dict[str, Any]:
        error = self._errors.get(plugin_id)
        manifest = self._manifests.get(plugin_id)
        if manifest:
            return self._state_builder.build(plugin_id, manifest, self._plugins.get(plugin_id), error)
        if error:
            return self._state_builder.build_error(plugin_id, error)
        raise KeyError(plugin_id)

    async def _emit_state(self, plugin_id: str):
        if plugin_id not in self._manifests and plugin_id not in self._errors:
            return
        await self.event_bus.emit("plugin.state.local", self._build_state(plugin_id))

    async def _emit_all_states(self):
        for plugin_id in sorted(set(self._manifests) | set(self._errors)):
            await self._emit_state(plugin_id)
