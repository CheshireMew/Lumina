from __future__ import annotations

from typing import Any

from core.interfaces.plugin import Plugin
from core.manifest import PluginManifest, normalize_capability_id

SELECTABLE_PROVIDER_CAPABILITIES = {"stt", "tts", "memory", "tool.search"}


def ui_category(capability: str) -> str:
    root = normalize_capability_id(capability).split(".")[0]
    if root in {"stt", "tts", "memory"}:
        return root
    if root == "tool":
        return "skill"
    return "system"


def is_selectable_provider(manifest: PluginManifest) -> bool:
    return manifest.kind == "provider" and manifest.capability in SELECTABLE_PROVIDER_CAPABILITIES


class PluginStateBuilder:
    def __init__(self, config: Any):
        self.config = config

    def build_all(
        self,
        manifests: dict[str, PluginManifest],
        plugins: dict[str, Plugin],
        errors: dict[str, str],
    ) -> list[dict[str, Any]]:
        states = [
            self.build(plugin_id, manifest, plugins.get(plugin_id), errors.get(plugin_id))
            for plugin_id, manifest in sorted(manifests.items())
        ]
        states.extend(
            self.build_error(plugin_id, error)
            for plugin_id, error in sorted(errors.items())
            if plugin_id not in manifests
        )
        return states

    def build(
        self,
        plugin_id: str,
        manifest: PluginManifest,
        plugin: Plugin | None,
        error: str | None,
    ) -> dict[str, Any]:
        metadata = plugin.get_metadata() if plugin else {
            "id": plugin_id,
            "name": plugin_id,
            "description": "",
            "kind": manifest.kind,
            "provides": manifest.provides,
        }
        desired_enabled = self._desired_enabled(plugin_id)
        selectable_provider = is_selectable_provider(manifest)
        selected_provider = self._selected_provider(manifest.capability) if selectable_provider else None
        status = "error" if error else ("ready" if plugin and plugin.enabled else "stopped")
        return {
            "id": plugin_id,
            "name": metadata.get("name", plugin_id),
            "description": metadata.get("description", ""),
            "kind": metadata.get("kind", manifest.kind),
            "category": ui_category(manifest.capability),
            "enabled": desired_enabled,
            "desired_enabled": desired_enabled,
            "active": bool(plugin and plugin.enabled),
            "active_in_group": selected_provider == plugin_id if selected_provider else bool(plugin and plugin.enabled),
            "group_id": manifest.capability if selectable_provider else plugin_id,
            "group_policy": "exclusive" if selectable_provider else "independent",
            "group_exclusive": selectable_provider,
            "capabilities": manifest.all_capabilities(),
            "runtime_target": manifest.runtime_target,
            "current_config": self._plugin_settings(plugin_id),
            "permissions": manifest.permissions,
            "func_tag": metadata.get("func_tag", manifest.kind.title()),
            "tags": metadata.get("tags", []),
            "computed_status": "error" if error else ("running" if plugin and plugin.enabled else "stopped"),
            "active_status": status,
            "error": error,
        }

    def build_error(self, plugin_id: str, error: str) -> dict[str, Any]:
        return {
            "id": plugin_id,
            "name": plugin_id,
            "description": "",
            "kind": "invalid",
            "category": "system",
            "enabled": False,
            "desired_enabled": False,
            "active": False,
            "active_in_group": False,
            "group_id": plugin_id,
            "group_policy": "independent",
            "group_exclusive": False,
            "capabilities": [],
            "runtime_target": "main",
            "current_config": self._plugin_settings(plugin_id),
            "permissions": [],
            "func_tag": "Error",
            "tags": [],
            "computed_status": "error",
            "active_status": "error",
            "error": error,
        }

    def _desired_enabled(self, plugin_id: str) -> bool:
        if self.config:
            return bool(self.config.is_plugin_desired_enabled(plugin_id))
        return True

    def _selected_provider(self, capability: str) -> str | None:
        if self.config:
            return self.config.get_selected_provider(capability)
        return None

    def _plugin_settings(self, plugin_id: str) -> dict[str, Any]:
        if not self.config:
            return {}
        return self.config.get_plugin_settings(plugin_id)
