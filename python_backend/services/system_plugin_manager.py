import os
import logging
from typing import Dict, List, Tuple, Optional
from core.interfaces.plugin import BaseSystemPlugin
# LuminaContext
from core.api.context import LuminaContext
# Manifest
import yaml
from core.manifest import PluginManifest
import importlib.util
from pathlib import Path
import sys
import inspect

logger = logging.getLogger("SystemPluginManager")


from services.plugins.discovery import PluginScanner
from services.plugins.dependencies import DependencySorter
from services.plugins.loader import PluginLoader

class SystemPluginManager:
    """
    Registry and Lifecycle Manager for System Plugins.
    Refactored to use dedicated components for Discovery/Loading.
    """
    def __init__(self, container=None):
        self.plugins: Dict[str, BaseSystemPlugin] = {}
        self.container = container
        self._load_plugins()

    def _load_plugins(self):
        logger.info("🧩 Plugin System: Starting Discovery...")
        
        # 1. Discovery
        current_dir = os.path.dirname(os.path.abspath(__file__))
        plugins_root_dir = Path(current_dir) / ".." / "plugins" / "system"
        
        scanner = PluginScanner(plugins_root_dir)
        manifests = scanner.scan()
        logger.info(f"🧩 Discovered {len(manifests)} valid plugin manifests.")
        
        # 2. Dependency Sorting
        try:
            sorter = DependencySorter(manifests)
            ordered_manifests = sorter.sort()
        except Exception as e:
            logger.error(f"Plugin Dependency Error: {e}")
            return


        # 3. Loading & Instantiation
        loader = PluginLoader()
        loaded_count = 0
        
        for manifest in ordered_manifests:
            instance = loader.load_plugin_class(manifest)
            if instance:
                # 4. Dependency Injection & Init
                if self.container:
                    instance.container = self.container
                
                try:
                    # Context Injection Logic
                    if self.container:
                        event_bus = getattr(self.container, 'event_bus', None)
                        
                        # Use SandboxedContext if permissions exist
                        if manifest and manifest.permissions:
                            from core.api.sandboxed_context import SandboxedContext
                            context = SandboxedContext(
                                self.container, 
                                event_bus=event_bus,
                                permissions=manifest.permissions
                            )
                            logger.info(f"🛡️ Using SandboxedContext for {manifest.id}")
                        else:
                            # Default Context
                            from core.api.context import LuminaContext
                            context = LuminaContext(self.container, event_bus=event_bus)
                        
                        # Initialize with Context
                        instance.initialize(context)
                    else:
                        # Fallback for no container (testing?)
                        instance.initialize(None)

                    self.plugins[manifest.id] = instance
                    loaded_count += 1
                    
                    # Register Routes if present
                    if instance.enabled and hasattr(instance, 'llm_routes') and instance.llm_routes:
                        from services.container import services
                        llm_manager = services.get_llm_manager()
                        for route in instance.llm_routes:
                            llm_manager.register_route(route)
                            
                except Exception as e:
                    logger.error(f"Plugin '{manifest.id}' failed to initialize: {e}")

        logger.info(f"✅ Plugin System Ready: {loaded_count}/{len(manifests)} plugins loaded.")





    def get_plugin(self, plugin_id: str) -> BaseSystemPlugin:
        # User might pass "voice-security" or "system.voice-security"
        # Since we defined ID as "system.voice-security", exact match preferred.
        # But for robust API handling:
        if plugin_id in self.plugins:
            return self.plugins[plugin_id]
        
        # Fallback check
        if not plugin_id.startswith("system."):
             alt_id = f"system.{plugin_id}"
             if alt_id in self.plugins:
                 return self.plugins[alt_id]
                 
        return None

    def list_plugins(self) -> List[dict]:
        """Returns list of plugin status dicts."""
        return [p.get_status() for p in self.plugins.values()]

    def reload_plugin(self, plugin_id: str) -> bool:
        """
        Hot Reload logic:
        1. Terminate old instance
        2. Clear sys.modules
        3. Reload from Manifest
        4. Re-initialize
        """
        logger.info(f"🔃 Reloading plugin: {plugin_id}")
        
        # 1. Identify Target
        old_plugin = self.get_plugin(plugin_id)
        if not old_plugin:
            logger.warning(f"Reload failed: Plugin {plugin_id} not found.")
            # Maybe it's a new install? allow trying to load specific ID?
            return self._load_single_plugin_by_id(plugin_id)

        # 2. Terminate
        try:
            old_plugin.terminate()
        except Exception as e:
            logger.error(f"Error terminating {plugin_id}: {e}")

        # 3. Locate Manifest to find module
        # We need to find the manifest file again.
        # Assuming plugins/system/{safe_name}
        safe_name = plugin_id.split(".")[-1]
        plugin_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "plugins" / "system" / safe_name / "manifest.yaml"
        
        if not plugin_path.exists():
             logger.error(f"Reload failed: Manifest not found at {plugin_path}")
             return False

        # 4. Clear sys.modules (Brute force for now, best effort)
        # We know module prefix is plugins.system.{safe_name}
        prefix = f"plugins.system.{safe_name}"
        to_delete = [m for m in sys.modules if m.startswith(prefix)]
        for m in to_delete:
            del sys.modules[m]
        
        # 5. Load New Instance
        try:
            result = self._load_from_manifest(plugin_path)
            if not result:
                logger.error(f"Reload failed: Could not load from manifest")
                return False
            
            new_plugin, _ = result
            
            # 6. Initialize (Inject Context)
            if self.container:
                 event_bus = getattr(self.container, 'event_bus', None)
                 manifest = getattr(new_plugin, '_manifest', None)
                 
                 if manifest and manifest.permissions:
                     from core.api.sandboxed_context import SandboxedContext
                     context = SandboxedContext(
                         self.container, 
                         event_bus=event_bus,
                         permissions=manifest.permissions
                     )
                 else:
                     context = LuminaContext(self.container, event_bus=event_bus)
                 
                 new_plugin.initialize(context)

            # 7. Update Registry
            self.plugins[plugin_id] = new_plugin
            logger.info(f"✅ Plugin {plugin_id} reloaded successfully.")
            
            # ⚡ Register LLM Routes (Reload)
            if hasattr(new_plugin, 'llm_routes') and new_plugin.llm_routes:
                from services.container import services
                llm_manager = services.get_llm_manager()
                for route in new_plugin.llm_routes:
                    llm_manager.register_route(route)
                    
            return True

        except Exception as e:
            logger.error(f"Reload CRITICAL failure: {e}")
            return False

    def _load_single_plugin_by_id(self, plugin_id: str) -> bool:
        """Helper to load a brand new plugin by ID (guessing path)"""
        safe_name = plugin_id.split(".")[-1]
        plugin_path = Path(os.path.dirname(os.path.abspath(__file__))) / ".." / "plugins" / "system" / safe_name / "manifest.yaml"
        
        if not plugin_path.exists():
            return False
            
        # Manually trigger load logic to avoid recursion loop with reload_plugin
        # This duplicates logic from reload_plugin but skips termination/module cleanup (as it's new)
        try:
             result = self._load_from_manifest(plugin_path)
             if not result:
                 return False
             
             new_plugin, _ = result
             
             if self.container:
                 event_bus = getattr(self.container, 'event_bus', None)
                 manifest = getattr(new_plugin, '_manifest', None)
                 
                 if manifest and manifest.permissions:
                     from core.api.sandboxed_context import SandboxedContext
                     context = SandboxedContext(
                         self.container, 
                         event_bus=event_bus,
                         permissions=manifest.permissions
                     )
                 else:
                     context = LuminaContext(self.container, event_bus=event_bus)
                 
                 new_plugin.initialize(context)
                 
             self.plugins[plugin_id] = new_plugin
             logger.info(f"✅ Plugin {plugin_id} loaded successfully (Hot Load).")
             
             # ⚡ Register LLM Routes (Hot Load)
             if hasattr(new_plugin, 'llm_routes') and new_plugin.llm_routes:
                 from services.container import services
                 llm_manager = services.get_llm_manager()
                 for route in new_plugin.llm_routes:
                     llm_manager.register_route(route)
                     
             return True
        except Exception as e:
             logger.error(f"Hot Load error for {plugin_id}: {e}")
             return False

    def set_plugin_state(self, plugin_id: str, enabled: bool) -> bool:
        """
        Unified State Management.
        Persists state and triggers lifecycle events (Reload/Terminate).
        """
        plugin = self.get_plugin(plugin_id)
        if not plugin:
            logger.warning(f"Cannot set state for known plugin {plugin_id}")
            return False

        current_state = plugin.enabled
        if current_state == enabled:
            return True # No change

        logger.info(f"🔌 Changing Plugin {plugin_id} state: {current_state} -> {enabled}")

        try:
            # 1. Persist Config
            # We try to use the plugin's internal config updater first
            try:
                plugin.enabled = enabled
            except Exception as e:
                logger.warning(f"Failed to persist config via plugin property: {e}")
                # Fallback? (Manifest is read-only usually, config is in data/)
        
            # 2. Lifecycle
            if not enabled:
                # Disable: Terminate cleanly
                try:
                    plugin.terminate()
                except Exception as e:
                    logger.error(f"Error terminating {plugin_id}: {e}")
                
            else:
                # Enable: Hot Reload to ensure fresh start
                # This re-reads the config we just saved (hopefully)
                if not self.reload_plugin(plugin_id):
                    return False
                
                # [NEW] Enforce Group Exclusivity
                self._enforce_group_exclusivity(plugin_id)
                
            return True

        except Exception as e:
            logger.error(f"State change failed for {plugin_id}: {e}")
            return False

    def _enforce_group_exclusivity(self, active_plugin_id: str):
        """
        If the newly enabled plugin belongs to a group, ensure it is the ONLY one active.
        """
        active_plugin = self.get_plugin(active_plugin_id)
        if not active_plugin: return

        # Get the group ID
        # Try Property -> Manifest -> None
        manifest = getattr(active_plugin, '_manifest', None)
        group_id = getattr(active_plugin, 'group_id', getattr(manifest, 'group_id', None))
        
        if not group_id:
            return # Independent plugin
            
        # Check Exclusivity Flag (Default True)
        # We check the ACITVE plugin's preference. If IT thinks the group is exclusive, it clears the room.
        is_exclusive = getattr(active_plugin, 'group_exclusive', True)
        if hasattr(active_plugin, '_manifest') and active_plugin._manifest:
             is_exclusive = getattr(active_plugin._manifest, 'group_exclusive', True)
             
        if not is_exclusive:
            logger.info(f"⚖️ Group '{group_id}' is Non-Exclusive. Allowing multiple plugins.")
            return

        logger.info(f"⚖️ Enforcing exclusivity for Group: '{group_id}' (Winner: {active_plugin_id})")

        # Iterate all other plugins
        for other_id, other_plugin in self.plugins.items():
            if other_id == active_plugin_id: continue
            
            # Check if same group
            other_manifest = getattr(other_plugin, '_manifest', None)
            other_group = getattr(other_plugin, 'group_id', getattr(other_manifest, 'group_id', None))
            
            if other_group == group_id and other_plugin.enabled:
                logger.warning(f"⛔ Auto-disabling conflicting plugin: {other_id}")
                # Recursively call set_plugin_state (to persist config & terminate)
                # But be careful of infinite loops -> we are setting to FALSE, so it won't re-trigger exclusivity
                self.set_plugin_state(other_id, False)


