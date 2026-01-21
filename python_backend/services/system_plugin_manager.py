import logging
import asyncio
from typing import Dict, List, Optional, Any

from core.interfaces.plugin import BaseSystemPlugin
# [Fix] CapabilityType is defined in schemas
from core.capabilities.schemas import CapabilityType
from services.plugins.registry import PluginRegistry
from services.plugins.lifecycle import PluginLifecycleManager
from services.plugins.sync import PluginStateSynchronizer
from services.plugins.dispatcher import PluginDispatcher

from core.events.bus import bus
from core.events.definitions import PluginLifecycleRequest, PluginLoadedPayload, PluginErrorPayload, PluginDisabledPayload
from app_config import config

logger = logging.getLogger("SystemPluginManager")

class SystemPluginManager:
    """
    [Facade] Unified access point for the Plugin System.
    Delegates responsibilities to specialized sub-components.
    
    Components:
    - registry: Dictionary of plugins, Discovery, Sorting.
    - lifecycle: Start, Stop, Reload.
    - sync: Updates to/from SurrealDB (SSOT).
    - dispatcher: Pushing plugins to worker processes.
    """
    def __init__(self, container=None, router_manager=None):
        # 1. Initialize Registry
        self.registry = PluginRegistry(container, router_manager)
        
        # 2. Initialize Dispatcher
        self.dispatcher = PluginDispatcher(self.registry)
        
        # 3. Initialize Lifecycle
        # Lifecycle uses registry to act on plugins
        self.lifecycle = PluginLifecycleManager(self.registry)
        
        # 4. Initialize Synchronizer
        # Syncs state between Registry and DB, using Lifecycle to actuate changes
        self.sync = PluginStateSynchronizer(self.registry, self.lifecycle)
        
        # Inject sync back into lifecycle (circular dependency resolution)
        self.lifecycle.synchronizer = self.sync

        # Backward Compatibility Attributes
        self.container = container
        self.router_manager = router_manager

    @property
    def plugins(self) -> Dict[str, BaseSystemPlugin]:
        return self.registry.plugins

    @property
    def disabled_manifests(self):
        return self.registry.disabled_manifests

    async def start(self):
        """Facade for System Start Sequence"""
        logger.info("🚀 SystemPluginManager: Starting up...")
        
        # 1. Connect Sync Bus
        await self.sync.connect()
        
        # 2. Discover & Load (Memory)
        self.registry.load_all_plugins()
        
        # 3. Sync with DB (Restore State)
        await self.sync.sync_with_db()
        
        # 4. Initialize Instances (Async)
        await self.lifecycle.initialize_all()
        
        # 5. Dispatch to Workers
        await self.dispatcher.distribute_plugins()
        
        # 6. Subscribe to Bus Events
        self._subscribe_events()
        
        logger.info("✨ SystemPluginManager: Ready.")

    def _subscribe_events(self):
        bus.subscribe("plugin.lifecycle.request_enable", self._on_enable_request)
        bus.subscribe("plugin.lifecycle.request_disable", self._on_disable_request)

    async def _on_enable_request(self, event):
        pid = event.data.plugin_id
        try:
            success = self.lifecycle.enable_plugin(pid)
            if success:
                # Initialize call if needed happens inside enable_plugin or we do it here?
                # For now enable_plugin does load.
                plugin = self.get_plugin(pid)
                if plugin and hasattr(plugin, 'initialize'):
                     # Clean async handling wrapper
                     import inspect
                     if inspect.iscoroutinefunction(plugin.initialize):
                         await plugin.initialize(getattr(plugin, 'context', None))
                     else:
                         plugin.initialize(getattr(plugin, 'context', None))

                # [Fix] Use canonical field names
                await self.sync.broadcast_state_change(pid, {
                    "desired_enabled": True,
                    "active_status": "ready"
                })
                await bus.emit("plugin.lifecycle.enabled", PluginLoadedPayload(plugin_id=pid, enabled=True))
                
                # [Aggregator] Emit state for centralized cache
                await self._emit_local_state(pid, enabled=True)
        except Exception as e:
            logger.error(f"Enable Event Failed: {e}")

    async def _on_disable_request(self, event):
        pid = event.data.plugin_id
        try:
            success = self.lifecycle.disable_plugin(pid)
            if success:
                # [Fix] Use canonical field names
                await self.sync.broadcast_state_change(pid, {
                    "desired_enabled": False,
                    "active_status": "stopped"
                })
                await bus.emit("plugin.lifecycle.disabled", PluginDisabledPayload(plugin_id=pid, reason="manual"))
                
                # [Aggregator] Emit state for centralized cache
                await self._emit_local_state(pid, enabled=False)
        except Exception as e:
             logger.error(f"Disable Event Failed: {e}")

    async def _emit_local_state(self, plugin_id: str, enabled: bool):
        """Emit plugin state to aggregator"""
        plugin = self.get_plugin(plugin_id)
        manifest = None
        
        if plugin:
            manifest = getattr(plugin, '_manifest', None)
        else:
            manifest = self.registry.disabled_manifests.get(plugin_id)
        
        state = {
            "id": plugin_id,
            "name": getattr(manifest, 'name', plugin_id) if manifest else plugin_id,
            "category": getattr(manifest, 'category', 'system') if manifest else 'system',
            "desired_enabled": enabled,
            "active_status": "ready" if enabled else "stopped",
            "runtime_target": "main",
            "worker_id": "main",
        }
        
        await bus.emit("plugin.state.local", state)

    # --- Facade Methods ---

    def get_plugin(self, plugin_id: str) -> Optional[BaseSystemPlugin]:
        return self.registry.get_plugin(plugin_id)

    def list_plugins(self) -> List[dict]:
        return self.registry.list_plugins()

    def reload_plugin(self, plugin_id: str) -> bool:
        return self.lifecycle.reload_plugin(plugin_id)

    def disable_plugin(self, plugin_id: str) -> bool:
        return self.lifecycle.disable_plugin(plugin_id)

    def enable_plugin(self, plugin_id: str) -> bool:
        return self.lifecycle.enable_plugin(plugin_id)

    def find_provider(self, cap_type: CapabilityType, **attributes) -> Optional[str]:
        return self.registry.find_provider(cap_type, **attributes)

    def get_active_ui_slots(self) -> List[dict]:
        """Return UI slots from all active plugins."""
        slots = []
        for pid, plugin in self.plugins.items():
            if not plugin.enabled:
                continue
            status = plugin.get_status()
            ui_slots = status.get("ui_slots", [])
            for slot in ui_slots:
                slot["_source"] = "system"
                slot["_plugin_id"] = pid
                slots.append(slot)
        return slots
