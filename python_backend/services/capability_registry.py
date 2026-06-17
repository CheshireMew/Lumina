from __future__ import annotations

from dataclasses import dataclass
from typing import Callable

from core.manifest import normalize_capability_id
from core.runtime import normalize_runtime_target


@dataclass
class CapabilityProvider:
    module_id: str
    capability: str
    runtime_target: str
    kind: str
    enabled: bool = False

    @property
    def is_provider(self) -> bool:
        return self.kind == "provider"


class CapabilityRegistry:
    def __init__(self):
        self._providers_by_capability: dict[str, list[CapabilityProvider]] = {}
        self._providers_by_module: dict[str, list[CapabilityProvider]] = {}

    def register_module(self, module_id: str, capabilities: list[str], runtime_target: str, kind: str, enabled: bool):
        self.unregister_module(module_id)
        normalized_target = normalize_runtime_target(runtime_target)
        providers: list[CapabilityProvider] = []
        for item in capabilities:
            normalized = normalize_capability_id(item)
            provider = CapabilityProvider(
                module_id=module_id,
                capability=normalized,
                runtime_target=normalized_target,
                kind=kind,
                enabled=enabled,
            )
            self._providers_by_capability.setdefault(normalized, []).append(provider)
            providers.append(provider)
        self._providers_by_module[module_id] = providers

    def unregister_module(self, module_id: str):
        providers = self._providers_by_module.pop(module_id, [])
        for provider in providers:
            current = self._providers_by_capability.get(provider.capability, [])
            self._providers_by_capability[provider.capability] = [
                item for item in current if item.module_id != module_id
            ]
            if not self._providers_by_capability[provider.capability]:
                self._providers_by_capability.pop(provider.capability, None)

    def set_enabled(self, module_id: str, enabled: bool):
        for provider in self._providers_by_module.get(module_id, []):
            provider.enabled = enabled

    def list_capability(self, capability: str) -> list[CapabilityProvider]:
        return list(self._providers_by_capability.get(normalize_capability_id(capability), []))

    def find_provider(
        self,
        capability: str,
        runtime_target: str | None = None,
        selected_provider: str | None = None,
        only_enabled: bool = True,
        predicate: Callable[[CapabilityProvider], bool] | None = None,
    ) -> str | None:
        normalized_target = normalize_runtime_target(runtime_target) if runtime_target else None
        candidates = self.list_capability(capability)
        for provider in candidates:
            if normalized_target and provider.runtime_target != normalized_target:
                continue
            if only_enabled and not provider.enabled:
                continue
            if predicate and not predicate(provider):
                continue
            if selected_provider and provider.module_id == selected_provider:
                return provider.module_id

        for provider in candidates:
            if normalized_target and provider.runtime_target != normalized_target:
                continue
            if only_enabled and not provider.enabled:
                continue
            if predicate and not predicate(provider):
                continue
            return provider.module_id
        return None
