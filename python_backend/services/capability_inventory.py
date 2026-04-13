from __future__ import annotations

import io
import shutil
import tempfile
import zipfile
from pathlib import Path
from typing import Any

import yaml

from core.manifest import PluginManifest
from core.runtime import list_capability_contracts
from services.chat.contracts import list_chat_hook_specs


class CapabilityInventoryService:
    def __init__(self, container):
        self.container = container

    def _list_plugin_snapshot(self) -> list[dict[str, Any]]:
        aggregator = getattr(self.container, "plugin_state_aggregator", None)
        if aggregator:
            snapshot = aggregator.get_snapshot()
            if snapshot:
                return snapshot

        spm = getattr(self.container, "system_plugin_manager", None)
        return spm.list_plugins() if spm else []

    def list_capabilities(self) -> list[dict[str, Any]]:
        plugins = self._list_plugin_snapshot()
        grouped: dict[str, dict[str, Any]] = {}

        for contract in list_capability_contracts():
            grouped[contract["capability"]] = {
                "capability": contract["capability"],
                "contract_version": contract["version"],
                "runtime_target": contract["runtime_target"],
                "supported_operations": contract["supported_operations"],
                "worker_routes": contract["worker_routes"],
                "stream_routes": contract["stream_routes"],
                "providers": [],
            }

        for plugin in plugins:
            for capability in plugin.get("capabilities", []):
                grouped.setdefault(
                    capability,
                    {
                        "capability": capability,
                        "contract_version": "1.0",
                        "runtime_target": plugin.get("runtime_target", "main"),
                        "supported_operations": [],
                        "worker_routes": {},
                        "stream_routes": {},
                        "providers": [],
                    },
                )
                grouped[capability]["providers"].append(
                    {
                        "plugin_id": plugin["id"],
                        "name": plugin["name"],
                        "kind": plugin.get("kind"),
                        "enabled": plugin.get("enabled", False),
                        "active": plugin.get("active", False),
                        "runtime_target": plugin.get("runtime_target", "main"),
                    }
                )

        llm_manager = getattr(self.container, "llm_manager", None)
        if llm_manager:
            grouped.setdefault(
                "llm",
                {
                    "capability": "llm",
                    "contract_version": "1.0",
                    "runtime_target": "main",
                    "supported_operations": [],
                    "worker_routes": {},
                    "stream_routes": {},
                    "providers": [],
                },
            )
            grouped["llm"]["providers"].extend(
                {
                    "plugin_id": f"driver.llm.{provider.id}",
                    "name": provider.id,
                    "kind": "provider",
                    "enabled": provider.enabled,
                    "active": any(route.provider_id == provider.id for route in llm_manager.list_routes()),
                    "runtime_target": "main",
                }
                for provider in llm_manager.list_providers()
            )

        return sorted(grouped.values(), key=lambda item: item["capability"])

    async def build_debug_snapshot(self) -> dict[str, Any]:
        spm = getattr(self.container, "system_plugin_manager", None)
        aggregator = getattr(self.container, "plugin_state_aggregator", None)
        items = self._list_plugin_snapshot()

        plugin_items: list[dict[str, Any]] = []
        for item in items:
            plugin = spm.get_plugin(item["id"]) if spm else None
            health = {}
            if plugin and hasattr(plugin, "health"):
                try:
                    health = await plugin.health()
                except Exception as exc:
                    health = {"status": "error", "detail": str(exc)}
            plugin_items.append({**item, "health": health})

        return {
            "plugins": plugin_items,
            "manifest_errors": spm.list_manifest_errors() if spm else {},
            "aggregator": aggregator.debug_dump() if aggregator else {},
            "chat_slots": list_chat_hook_specs(),
            "capabilities": self.list_capabilities(),
        }

    def marketplace_snapshot(self) -> dict[str, Any]:
        return {
            "schema_version": "1.0",
            "installed": self._list_plugin_snapshot(),
            "discoverable": [],
            "notes": "Marketplace catalog is reserved but not connected to a remote index yet.",
        }

    async def install_plugin_from_zip(self, file_obj, filename: str | None = None) -> dict[str, Any]:
        payload = file_obj.read()
        if not payload:
            raise ValueError("Plugin package is empty")

        archive_name = filename or "plugin.zip"
        if not archive_name.lower().endswith(".zip"):
            raise ValueError("Plugin package must be a .zip archive")

        extensions_root = Path(__file__).resolve().parent.parent / "plugins" / "extensions"
        extensions_root.mkdir(parents=True, exist_ok=True)

        with tempfile.TemporaryDirectory(prefix="lumina_plugin_install_") as tmp_dir:
            tmp_path = Path(tmp_dir)
            with zipfile.ZipFile(io.BytesIO(payload)) as archive:
                members = [Path(info.filename) for info in archive.infolist() if not info.is_dir()]
                if not members:
                    raise ValueError("Plugin package contains no files")
                for member in members:
                    if member.is_absolute() or ".." in member.parts:
                        raise ValueError(f"Unsafe plugin archive entry: {member}")
                archive.extractall(tmp_path)

            manifest_paths = list(tmp_path.rglob("manifest.yaml"))
            if len(manifest_paths) != 1:
                raise ValueError("Plugin package must contain exactly one manifest.yaml")

            manifest_path = manifest_paths[0]
            plugin_root = manifest_path.parent
            raw_manifest = yaml.safe_load(manifest_path.read_text(encoding="utf-8")) or {}
            manifest = PluginManifest(**{**raw_manifest, "path": str(plugin_root)})

            target_dir = extensions_root / plugin_root.name
            if target_dir.exists():
                raise ValueError(f"Plugin directory already exists: {target_dir.name}")

            shutil.copytree(plugin_root, target_dir)

        spm = getattr(self.container, "system_plugin_manager", None)
        if spm:
            spm.refresh_manifests()
            await spm._emit_all_states()

        return {
            "success": True,
            "plugin_id": manifest.id,
            "installed_path": str(target_dir),
        }
