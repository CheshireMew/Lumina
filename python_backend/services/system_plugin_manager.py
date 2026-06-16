import logging
from pathlib import Path
from typing import Any

from core.events.bus import bus
from core.events.definitions import PluginLifecycleRequest
from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest, normalize_capability_id
from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target
from services.capability_registry import CapabilityRegistry
from services.plugin_kernel import (
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
    def __init__(self, container=None, runtime_target: str = MAIN_RUNTIME_TARGET, base_dir: Path | None = None):
        self.container = container
        self.event_bus = container.get_event_bus() if container and container.has_service("event_bus") else bus
        self.runtime_target = normalize_runtime_target(runtime_target)
        self._plugin_root = Path(base_dir) if base_dir else Path(__file__).parent.parent / "plugins"
        self._plugins: dict[str, Plugin] = {}
        self._manifests: dict[str, PluginManifest] = {}
        self._errors: dict[str, str] = {}
        self._capability_registry = container.get_capability_registry() if container and container.get_capability_registry() else CapabilityRegistry()
        if container is not None:
            container.set_capability_registry(self._capability_registry)
        self._manifest_repository = ManifestRepository(self._plugin_root)
        self._loader = PluginLoader()
        self._permission_checker = PermissionChecker()
        self._context_binder = PluginContextBinder(container, self._capability_registry)
        self._state_builder = PluginStateBuilder(container.get_config() if container and container.has_service("config") else None)
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
            if not self.container.get_config().is_plugin_desired_enabled(plugin_id):
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
        request = self._require_lifecycle_request(event)
        await self.enable_plugin(request.plugin_id)

    async def _on_disable_request(self, event):
        request = self._require_lifecycle_request(event)
        await self.disable_plugin(request.plugin_id)

    def _require_lifecycle_request(self, event) -> PluginLifecycleRequest:
        if not isinstance(event.data, PluginLifecycleRequest):
            raise TypeError(
                "plugin.lifecycle.request_* events must carry PluginLifecycleRequest"
            )
        return event.data

    def refresh_manifests(self):
        previous_manifest_ids = set(self._manifests)
        retained_load_errors = {
            plugin_id: error
            for plugin_id, error in self._errors.items()
            if plugin_id in self._plugins
        }
        result = self._manifest_repository.discover(self.runtime_target)
        self._manifests = {}
        self._errors = {**retained_load_errors, **result.errors}

        for plugin_id, manifest in result.manifests.items():
            package_id = getattr(manifest, "package", None)
            if not package_id:
                self._manifests[plugin_id] = manifest
                continue
            if self._is_package_ready(str(package_id)):
                self._manifests[plugin_id] = manifest
                continue
            self._errors[plugin_id] = f"package_unavailable:{package_id}"

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

    def _is_package_ready(self, package_id: str) -> bool:
        package_registry = self.container.get_capability_package_registry()
        if package_registry is None:
            return False
        snapshot = package_registry.resolve(package_id)
        return bool(snapshot and snapshot.status == "ready")

    async def _load_and_enable(self, plugin_id: str) -> Plugin | None:
        plugin = self._plugins.get(plugin_id)
        if plugin is None:
            plugin = await self._instantiate_plugin(plugin_id)
            if plugin is None:
                return None
        await plugin.enable()
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

    def is_plugin_desired_enabled(self, plugin_id: str) -> bool:
        return bool(self.container.get_config().is_plugin_desired_enabled(plugin_id))

    def find_provider(self, capability: str, runtime_target: str | None = None, **_: Any) -> str | None:
        normalized = normalize_capability_id(capability)
        selected = self.container.get_config().get_selected_provider(normalized)
        if selected is None and "." in normalized:
            selected = self.container.get_config().get_selected_provider(normalized.split(".")[0])
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
        persist = not self.container.get_config().is_read_only
        self._config_service.set_plugin_desired_state(plugin_id, True, persist=persist)
        plugin = await self._load_and_enable(plugin_id)
        if plugin and is_selectable_provider(manifest):
            self._config_service.set_selected_provider(manifest.capability, plugin_id, persist=persist)
        return plugin is not None

    async def disable_plugin(self, plugin_id: str) -> bool:
        plugin = self._plugins.get(plugin_id)
        manifest = self._manifests.get(plugin_id)
        persist = not self.container.get_config().is_read_only
        self._config_service.set_plugin_desired_state(plugin_id, False, persist=persist)
        if manifest and is_selectable_provider(manifest):
            current_provider = self.container.get_config().get_selected_provider(manifest.capability)
            if current_provider == plugin_id:
                self._config_service.clear_selected_provider(manifest.capability, persist=persist)
        if plugin:
            await plugin.disable()
        self._capability_registry.set_enabled(plugin_id, False)
        await self._emit_state(plugin_id)
        return True

    def reload_plugin(self, plugin_id: str) -> bool:
        logger.warning("Hot reload is disabled in the unified kernel: %s", plugin_id)
        return False

    async def shutdown(self):
        for sub_id in self._lifecycle_subscriptions:
            self.event_bus.unsubscribe(sub_id)
        self._lifecycle_subscriptions.clear()
        for plugin_id, plugin in list(self._plugins.items()):
            try:
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
