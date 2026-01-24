import logging
import asyncio

logger = logging.getLogger("PluginStateSynchronizer")

class PluginStateSynchronizer:
    """
    Manages Single Source of Truth (SSOT) via SurrealDB.
    Responsibilities:
    - Broadcasting lifecycle events (Enable/Disable) to DB.
    - Initial bi-directional sync (DB <-> Local Registry) on startup.
    - Providing frontend visibility into plugin states.
    """
    
    def __init__(self, registry, lifecycle_manager=None):
        self.registry = registry
        self.lifecycle_manager = lifecycle_manager # Injected late to avoid circular dep if needed
        self.lifecycle_bus = None

    async def connect(self):
        from services.infra.bus_factory import get_lifecycle_bus
        self.lifecycle_bus = get_lifecycle_bus()
        await self.lifecycle_bus.connect()

    async def broadcast_state_change(self, plugin_id: str, state: dict):
        """Publish update to Distributed Bus"""
        if not self.lifecycle_bus: return
        state["worker_id"] = "main"
        await self.lifecycle_bus.publish_state(plugin_id, state)

    async def sync_with_db(self):
        """
        Bidirectional Sync:
        1. DB -> Local (Restore Persistence)
        2. Local -> DB (Publish Metadata for UI)
        """
        logger.info("♻️ Synchronizing local state with SurrealDB SSOT...")
        try:
            # Wait for connection
            for i in range(5):
                if getattr(self.lifecycle_bus, "_is_connected", False): break
                logger.warning(f"⏳ Waiting for lifecycle_bus connection... ({i+1}/5)")
                await asyncio.sleep(1)
            
            if not getattr(self.lifecycle_bus, "_is_connected", False):
                logger.error("❌ Lifecycle Bus not connected, skipping sync")
                return

            # --- Phase 1: Read from DB ---
            # Using lifecycle manager to enact changes
            if self.lifecycle_manager:
                states = await self.lifecycle_bus.get_all_states()
                for pid, state in states.items():
                    if pid in self.registry.plugins or pid in self.registry.disabled_manifests:
                        # [Fix] Use desired_enabled (Intent) instead of legacy 'enabled'
                        db_desired = state.get("desired_enabled")
                        # Fallback to legacy 'enabled' for migration compatibility
                        if db_desired is None:
                            db_desired = state.get("enabled")
                        
                        if db_desired is not None:
                            is_active = pid in self.registry.plugins
                            if db_desired and not is_active:
                                logger.info(f"🔄 SSOT: Enabling {pid}")
                                self.lifecycle_manager.enable_plugin(pid)
                            elif not db_desired and is_active:
                                logger.info(f"🔄 SSOT: Disabling {pid}")
                                self.lifecycle_manager.disable_plugin(pid)

            # --- Phase 2: Write to DB ---
            await self._publish_local_state()

        except Exception as e:
            logger.warning(f"⚠️ Initial SSOT sync failed: {e}")

    async def _publish_local_state(self):
        success_count = 0
        joined_list = list(self.registry.plugins.items()) + list(self.registry.disabled_manifests.items())
        
        for pid, item in joined_list:
            # item is either Plugin Instance or Manifest
            manifest = getattr(item, '_manifest', None) or getattr(item, 'manifest', None)
            if not manifest and hasattr(item, 'description'): manifest = item # It IS a manifest
            
            # Logic to extract capabilities, config, etc. same as original
            capabilities = []
            if manifest and hasattr(manifest, 'provides'):
                for cap in manifest.provides:
                    cap_type = cap.type if hasattr(cap, 'type') else cap
                    if hasattr(cap_type, 'value'): capabilities.append(cap_type.value)
                    else: capabilities.append(str(cap_type))

            # Determine enabled status
            # If it's in registry.plugins, it's enabled.
            enabled = pid in self.registry.plugins
            
            state_data = {
                "id": pid,
                "name": getattr(manifest, 'name', pid),
                "category": getattr(manifest, 'category', 'system'),
                "description": getattr(manifest, 'description', ''),
                "version": getattr(manifest, 'version', '0.0.0'),
                # [Fix] Use canonical field names
                "desired_enabled": enabled,  # Intent
                "active_status": "ready" if enabled else "stopped",  # Reality
                # Legacy fields for backward compatibility with old consumers
                "enabled": enabled,
                "active": enabled,
                "runtime_target": "main",
                "worker_id": "main",
                "capabilities": capabilities,
                "group_policy": "independent",
                "permissions": getattr(manifest, 'permissions', []),
                "config_schema": getattr(manifest, 'config_schema', None),
                "ui_slots": getattr(manifest, 'ui_slots', []),
                "group_id": getattr(manifest, 'group_id', None),
                "group_exclusive": getattr(manifest, 'group_exclusive', False),
                "tags": getattr(manifest, 'tags', []),
                "active_in_group": False
            }
            
            try:
                await self.lifecycle_bus.publish_state(pid, state_data)
                success_count += 1
            except Exception as e:
                logger.error(f"Failed to publish {pid}: {e}")
                
        logger.info(f"✅ Published {success_count} plugin states to DB.")
