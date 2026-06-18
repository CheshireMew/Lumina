import logging
from pathlib import Path
from typing import Any

from core.events.definitions import CapabilityLifecycleRequest
from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest, normalize_capability_id
from core.runtime import MAIN_RUNTIME_TARGET, normalize_runtime_target
from services.capability_kernel import (
    CapabilityContextBinder,
    CapabilityModuleLoader,
    CapabilityStateBuilder,
    ManifestRepository,
    is_selectable_provider,
)

logger = logging.getLogger("CapabilityModuleManager")


class CapabilityModuleManager:
    def __init__(self, container, runtime_target: str = MAIN_RUNTIME_TARGET, base_dir: Path | None = None):
        if container is None:
            raise ValueError("CapabilityModuleManager requires ServiceContainer")

        self.container = container
        self.event_bus = self._require_service(container.get_event_bus(), "EventBus")
        self.runtime_target = normalize_runtime_target(runtime_target)
        self._module_root = Path(base_dir) if base_dir else Path(__file__).parent.parent / "capability_modules"
        self._modules: dict[str, CapabilityModule] = {}
        self._manifests: dict[str, CapabilityManifest] = {}
        self._errors: dict[str, str] = {}
        self._capability_registry = self._require_service(
            container.get_capability_registry(),
            "CapabilityRegistry",
        )
        config = self._require_service(container.get_config(), "Config")
        self._manifest_repository = ManifestRepository(self._module_root)
        self._loader = CapabilityModuleLoader()
        self._context_binder = CapabilityContextBinder(container, self._capability_registry)
        self._state_builder = CapabilityStateBuilder(config)
        self._lifecycle_subscriptions: list[int] = []

    def _require_service(self, value: Any, name: str) -> Any:
        if value is None:
            raise ValueError(f"CapabilityModuleManager requires {name}")
        return value

    @property
    def _config_service(self):
        from services.config_service import ConfigService

        return ConfigService(self.container)

    @property
    def modules(self) -> dict[str, CapabilityModule]:
        return self._modules

    async def start(self):
        logger.info("Starting capability module kernel for runtime %s", self.runtime_target)
        self._subscribe_lifecycle_requests()
        self.refresh_manifests()

        for module_id, manifest in self._manifests.items():
            if not self.container.get_config().is_provider_desired_enabled(module_id):
                continue
            await self._load_and_enable(module_id)

        await self._emit_all_states()
        logger.info("Capability module kernel ready")

    def _subscribe_lifecycle_requests(self):
        if self._lifecycle_subscriptions:
            return
        self._lifecycle_subscriptions.append(
            self.event_bus.subscribe("capability.lifecycle.request_enable", self._on_enable_request)
        )
        self._lifecycle_subscriptions.append(
            self.event_bus.subscribe("capability.lifecycle.request_disable", self._on_disable_request)
        )

    async def _on_enable_request(self, event):
        request = self._require_lifecycle_request(event)
        await self.enable_module(request.module_id)

    async def _on_disable_request(self, event):
        request = self._require_lifecycle_request(event)
        await self.disable_module(request.module_id)

    def _require_lifecycle_request(self, event) -> CapabilityLifecycleRequest:
        if not isinstance(event.data, CapabilityLifecycleRequest):
            raise TypeError(
                "capability.lifecycle.request_* events must carry CapabilityLifecycleRequest"
            )
        return event.data

    def refresh_manifests(self):
        previous_manifest_ids = set(self._manifests)
        retained_load_errors = {
            module_id: error
            for module_id, error in self._errors.items()
            if module_id in self._modules
        }
        result = self._manifest_repository.discover(self.runtime_target)
        self._manifests = {}
        self._errors = {**retained_load_errors, **result.errors}

        for module_id, manifest in result.manifests.items():
            runtime_id = getattr(manifest, "runtime", None)
            if not runtime_id:
                self._manifests[module_id] = manifest
                continue
            if self._is_runtime_ready(str(runtime_id)):
                self._manifests[module_id] = manifest
                continue
            self._errors[module_id] = f"runtime_unavailable:{runtime_id}"

        for module_id in previous_manifest_ids - set(self._manifests):
            self._capability_registry.unregister_module(module_id)

        for module_id, manifest in self._manifests.items():
            self._capability_registry.register_module(
                module_id=module_id,
                capabilities=manifest.all_capabilities(),
                runtime_target=manifest.runtime_target,
                kind=manifest.kind,
                enabled=bool(self._modules.get(module_id) and self._modules[module_id].enabled),
            )

    def _is_runtime_ready(self, runtime_id: str) -> bool:
        runtime_registry = self.container.get_worker_runtime_registry()
        snapshot = runtime_registry.resolve(runtime_id)
        return bool(snapshot and snapshot.status == "ready")

    async def _load_and_enable(self, module_id: str) -> CapabilityModule | None:
        module = self._modules.get(module_id)
        if module is None:
            module = await self._instantiate_module(module_id)
            if module is None:
                return None
        await module.enable()
        self._capability_registry.set_enabled(module_id, True)
        await self._emit_state(module_id)
        return module

    async def _instantiate_module(self, module_id: str) -> CapabilityModule | None:
        manifest = self._manifests.get(module_id)
        if manifest is None:
            return None

        try:
            module = self._loader.instantiate(manifest)
            await self._context_binder.bind(module, manifest)
            self._modules[module_id] = module
            self._errors.pop(module_id, None)
            return module
        except Exception as exc:
            logger.error("Failed to load capability module %s: %s", module_id, exc, exc_info=True)
            self._errors[module_id] = str(exc)
            return None

    def get_module(self, module_id: str) -> CapabilityModule | None:
        return self._modules.get(module_id)

    def get_manifest(self, module_id: str) -> CapabilityManifest | None:
        return self._manifests.get(module_id)

    def is_module_active(self, module_id: str) -> bool:
        module = self._modules.get(module_id)
        return bool(module and module.enabled)

    def is_module_desired_enabled(self, module_id: str) -> bool:
        return bool(self.container.get_config().is_provider_desired_enabled(module_id))

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

    def list_modules(self) -> list[dict[str, Any]]:
        return self._state_builder.build_all(self._manifests, self._modules, self._errors)

    def list_manifest_errors(self) -> dict[str, str]:
        return dict(self._errors)

    async def enable_module(self, module_id: str) -> bool:
        manifest = self._manifests.get(module_id)
        if manifest is None:
            return False
        persist = not self.container.get_config().is_read_only
        self._config_service.set_provider_desired_state(module_id, True, persist=persist)
        module = await self._load_and_enable(module_id)
        if module and is_selectable_provider(manifest):
            self._config_service.set_selected_provider(manifest.capability, module_id, persist=persist)
        return module is not None

    async def disable_module(self, module_id: str) -> bool:
        module = self._modules.get(module_id)
        manifest = self._manifests.get(module_id)
        persist = not self.container.get_config().is_read_only
        self._config_service.set_provider_desired_state(module_id, False, persist=persist)
        if manifest and is_selectable_provider(manifest):
            current_provider = self.container.get_config().get_selected_provider(manifest.capability)
            if current_provider == module_id:
                self._config_service.clear_selected_provider(manifest.capability, persist=persist)
        if module:
            await module.disable()
        self._capability_registry.set_enabled(module_id, False)
        await self._emit_state(module_id)
        return True

    def reload_module(self, module_id: str) -> bool:
        logger.warning("Hot reload is disabled in the capability module kernel: %s", module_id)
        return False

    async def shutdown(self):
        for sub_id in self._lifecycle_subscriptions:
            self.event_bus.unsubscribe(sub_id)
        self._lifecycle_subscriptions.clear()
        for module_id, module in list(self._modules.items()):
            try:
                if module.enabled:
                    await module.disable()
                await module.unload()
            finally:
                self._capability_registry.set_enabled(module_id, False)

    def _build_state(self, module_id: str) -> dict[str, Any]:
        error = self._errors.get(module_id)
        manifest = self._manifests.get(module_id)
        if manifest:
            return self._state_builder.build(module_id, manifest, self._modules.get(module_id), error)
        if error:
            return self._state_builder.build_error(module_id, error)
        raise KeyError(module_id)

    async def _emit_state(self, module_id: str):
        return

    async def _emit_all_states(self):
        for module_id in sorted(set(self._manifests) | set(self._errors)):
            await self._emit_state(module_id)
