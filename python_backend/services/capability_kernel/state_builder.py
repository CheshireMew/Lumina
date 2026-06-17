from __future__ import annotations

from typing import Any

from core.interfaces.module import CapabilityModule
from core.manifest import CapabilityManifest, normalize_capability_id

SELECTABLE_PROVIDER_CAPABILITIES = {"stt", "tts", "memory", "tool.search"}


def ui_category(capability: str) -> str:
    root = normalize_capability_id(capability).split(".")[0]
    if root in {"stt", "tts", "memory"}:
        return root
    if root == "tool":
        return "skill"
    return "system"


def is_selectable_provider(manifest: CapabilityManifest) -> bool:
    return manifest.kind == "provider" and manifest.capability in SELECTABLE_PROVIDER_CAPABILITIES


class CapabilityStateBuilder:
    def __init__(self, config: Any):
        if config is None:
            raise ValueError("CapabilityStateBuilder requires Config")
        self.config = config

    def build_all(
        self,
        manifests: dict[str, CapabilityManifest],
        modules: dict[str, CapabilityModule],
        errors: dict[str, str],
    ) -> list[dict[str, Any]]:
        states = [
            self.build(module_id, manifest, modules.get(module_id), errors.get(module_id))
            for module_id, manifest in sorted(manifests.items())
        ]
        states.extend(
            self.build_error(module_id, error)
            for module_id, error in sorted(errors.items())
            if module_id not in manifests
        )
        return states

    def build(
        self,
        module_id: str,
        manifest: CapabilityManifest,
        module: CapabilityModule | None,
        error: str | None,
    ) -> dict[str, Any]:
        metadata = module.get_metadata() if module else {
            "id": module_id,
            "name": module_id,
            "description": "",
            "kind": manifest.kind,
            "provides": manifest.provides,
        }
        desired_enabled = self._desired_enabled(module_id)
        selectable_provider = is_selectable_provider(manifest)
        selected_provider = self._selected_provider(manifest.capability) if selectable_provider else None
        status = "error" if error else ("ready" if module and module.enabled else "stopped")
        return {
            "id": module_id,
            "name": metadata.get("name", module_id),
            "description": metadata.get("description", ""),
            "kind": metadata.get("kind", manifest.kind),
            "category": ui_category(manifest.capability),
            "enabled": desired_enabled,
            "desired_enabled": desired_enabled,
            "active": bool(module and module.enabled),
            "active_in_group": selected_provider == module_id if selected_provider else bool(module and module.enabled),
            "group_id": manifest.capability if selectable_provider else module_id,
            "group_policy": "exclusive" if selectable_provider else "independent",
            "group_exclusive": selectable_provider,
            "capabilities": manifest.all_capabilities(),
            "runtime_target": manifest.runtime_target,
            "current_config": self._provider_settings(module_id),
            "permissions": manifest.permissions,
            "func_tag": metadata.get("func_tag", manifest.kind.title()),
            "tags": metadata.get("tags", []),
            "computed_status": "error" if error else ("running" if module and module.enabled else "stopped"),
            "active_status": status,
            "error": error,
        }

    def build_error(self, module_id: str, error: str) -> dict[str, Any]:
        return {
            "id": module_id,
            "name": module_id,
            "description": "",
            "kind": "invalid",
            "category": "system",
            "enabled": False,
            "desired_enabled": False,
            "active": False,
            "active_in_group": False,
            "group_id": module_id,
            "group_policy": "independent",
            "group_exclusive": False,
            "capabilities": [],
            "runtime_target": "main",
            "current_config": self._provider_settings(module_id),
            "permissions": [],
            "func_tag": "Error",
            "tags": [],
            "computed_status": "error",
            "active_status": "error",
            "error": error,
        }

    def _desired_enabled(self, module_id: str) -> bool:
        return bool(self.config.is_provider_desired_enabled(module_id))

    def _selected_provider(self, capability: str) -> str | None:
        return self.config.get_selected_provider(capability)

    def _provider_settings(self, module_id: str) -> dict[str, Any]:
        return self.config.get_provider_settings(module_id)
