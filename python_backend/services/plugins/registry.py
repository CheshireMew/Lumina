import os
import logging
from typing import Dict, List, Optional
from pathlib import Path
from collections import defaultdict

from core.interfaces.plugin import BaseSystemPlugin
from core.manifest import PluginManifest
from core.api.context import LuminaContext
from core.api.sandboxed_context import SandboxedContext
# [Fix] CapabilityType is in schemas
from core.capabilities.schemas import CapabilityType

from services.plugins.discovery import PluginScanner
from services.plugins.dependencies import DependencySorter
from services.plugins.loader import PluginLoader
from security.policy import SecurityPolicy
from app_config import config

logger = logging.getLogger("PluginRegistry")

class PluginRegistry:
    """
    Manages the in-memory state of the Plugin System.
    Responsibilities:
    - Discovery (Scanning)
    - Dependency Sorting
    - Loading & Container Injection (Initialization)
    - State Storage (Active Plugins, Disabled Manifests)
    - Capability Indexing
    """
    def __init__(self, container=None, router_manager=None):
        self.container = container
        self.router_manager = router_manager
        
        # State
        self.plugins: Dict[str, BaseSystemPlugin] = {}
        self.disabled_manifests: Dict[str, PluginManifest] = {}
        self.capability_index: Dict[CapabilityType, List[str]] = defaultdict(list)

    def load_all_plugins(self) -> int:
        """
        Scans, Sorts, and Loads all plugins from disk.
        Returns count of loaded plugins.
        """
        logger.info("🧩 Plugin Registry: Starting Discovery...")
        
        # 1. Discovery
        # registry.py is at services/plugins/registry.py
        # We need to get to python_backend/plugins
        # current_dir = services/plugins -> parent = services -> parent = python_backend
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_root = Path(current_dir).parent.parent / "plugins"
        
        manifests = []
        
        # Scan Core System Plugins
        system_dir = plugins_root / "system"
        if system_dir.exists():
            manifests.extend(PluginScanner(system_dir).scan())
            
        # Scan Extensions
        ext_dir = plugins_root / "extensions"
        if ext_dir.exists():
            manifests.extend(PluginScanner(ext_dir).scan())
            
        logger.info(f"🧩 Discovered {len(manifests)} valid plugin manifests.")
        
        # 2. Sorting
        try:
            ordered_manifests = DependencySorter(manifests).sort()
        except Exception as e:
            logger.error(f"Plugin Dependency Error: {e}")
            return 0

        # 3. Loading
        loader = PluginLoader()
        loaded_count = 0
        disabled_ids = set(config.plugins.disabled_plugins)

        for manifest in ordered_manifests:
            if manifest.id in disabled_ids:
                logger.info(f"💤 Plugin {manifest.id} is globally disabled (Lazy Load).")
                self.disabled_manifests[manifest.id] = manifest
                continue

            # Security Check
            is_allowed, warnings = SecurityPolicy.check_permissions(manifest)
            for warn in warnings:
                logger.warning(f"  [Security] {warn}")
            
            if not is_allowed:
                logger.error(f"⛔ Plugin {manifest.id} BLOCKED by Security Policy.")
                continue

            manifest = SecurityPolicy.enforce_isolation_policy(manifest)
            
            # Load Class/Stub
            instance = loader.load_plugin_class(manifest)
            
            if instance:
                if getattr(manifest, 'runtime_target', 'main') != 'main':
                     logger.info(f"🛰️ Loaded Remote Stub for {manifest.id} (Target: {manifest.runtime_target})")
                
                # Injection
                if self.container:
                    instance.container = self.container
                    self._inject_context(instance, manifest)

                self.plugins[manifest.id] = instance
                loaded_count += 1
                
                # Register Routes (Immediate)
                if instance.enabled and hasattr(instance, 'llm_routes') and instance.llm_routes:
                    self._register_llm_routes(instance.llm_routes)
        
        self.rebuild_index()
        logger.info(f"✅ Plugin Registry Ready: {loaded_count}/{len(manifests)} loaded.")
        return loaded_count
    
    def _inject_context(self, instance, manifest):
        try:
            event_bus = getattr(self.container, 'event_bus', None)
            if manifest and manifest.permissions:
                context = SandboxedContext(
                    self.container,
                    plugin_id=manifest.id,
                    event_bus=event_bus,
                    permissions=manifest.permissions,
                    router_manager=self.router_manager
                )
                logger.info(f"🛡️ Using SandboxedContext for {manifest.id}")
            else:
                context = LuminaContext(
                    self.container,
                    plugin_id=manifest.id,
                    event_bus=event_bus,
                    router_manager=self.router_manager
                )
            instance.context = context
        except Exception as e:
            logger.error(f"Context Injection Failed for {manifest.id}: {e}")

    def _register_llm_routes(self, routes):
        try:
            from services.container import services
            llm_manager = services.get_llm_manager()
            for route in routes:
                llm_manager.register_route(route)
        except Exception as e:
            logger.warning(f"LLM Route Registration failed: {e}")

    def rebuild_index(self):
        self.capability_index.clear()
        for pid, plugin in self.plugins.items():
            if not plugin.enabled: continue
            
            manifest = getattr(plugin, '_manifest', None)
            if not manifest: continue
            
            for cap in manifest.provides:
                self.capability_index[cap.type].append(pid)

    def get_plugin(self, plugin_id: str) -> Optional[BaseSystemPlugin]:
        if plugin_id in self.plugins:
            return self.plugins[plugin_id]
        # Fallback for short IDs
        if not plugin_id.startswith("system."):
             alt_id = f"system.{plugin_id}"
             if alt_id in self.plugins:
                 return self.plugins[alt_id]
        return None

    def list_plugins(self) -> List[dict]:
        """Returns list of plugin status dicts (Active + Disabled)."""
        active = []
        for p in self.plugins.values():
            status = p.get_status()
            active.append(status)
        
        disabled = []
        for pid, manifest in self.disabled_manifests.items():
            disabled.append({
                "id": pid,
                "name": getattr(manifest, 'name', pid),
                "description": getattr(manifest, 'description', "Disabled"),
                "version": getattr(manifest, 'version', "0.0.0"),
                "desired_enabled": False,  # Canonical
                "active_status": "stopped",  # Canonical
                "enabled": False,  # UI Compat
                "status": "disabled_lazy",
                "category": getattr(manifest, 'category', 'system'),
                "func_tag": getattr(manifest, 'func_tag', 'System Plugin'),
                "group_id": getattr(manifest, 'group_id', None),
                "group_exclusive": getattr(manifest, 'group_exclusive', True),
                "tags": getattr(manifest, 'tags', []),
                # [Fix] Full Metadata for Store
                "permissions": getattr(manifest, 'permissions', []),
                "config_schema": getattr(manifest, 'config_schema', None),
                "ui_slots": getattr(manifest, 'ui_slots', [])
            })
        return active + disabled

    def find_provider(self, cap_type: CapabilityType, **attributes) -> Optional[str]:
        candidates = self.capability_index.get(cap_type, [])
        if not candidates: return None
        
        for pid in candidates:
            plugin = self.get_plugin(pid)
            if not plugin: continue
            
            manifest = getattr(plugin, '_manifest', None)
            if not manifest: continue
            
            contract = next((c for c in manifest.provides if c.type == cap_type), None)
            if not contract: continue
            
            match = True
            for k, v in attributes.items():
                if contract.attributes.get(k) != v:
                    match = False
                    break
            
            if match: return pid
        return None
