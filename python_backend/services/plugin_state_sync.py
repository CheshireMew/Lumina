
import logging
import asyncio
from typing import Any, Dict
from services.infra.bus_factory import get_lifecycle_bus
from core.runtime import normalize_runtime_target

logger = logging.getLogger("PluginStateSync")

class PluginStateSync:
    """
    Worker-side service that synchronizes local plugin state 
    with the distributed Lifecycle Bus.
    
    [Architecture 6.0] Workers ONLY process plugins matching their runtime_target.
    """
    
    def __init__(self, plugin_manager, worker_id: str = None, expected_target: str = None, reporter=None):
        self.plugin_manager = plugin_manager
        self.bus = get_lifecycle_bus()
        import socket
        self.worker_id = worker_id or f"worker:{socket.gethostname()}"
        self.expected_target = normalize_runtime_target(expected_target)
        self.reporter = reporter # [Fix] Direct reference to Status Reporter
        self._desired_state_cache: Dict[str, bool] = {}

    def _get_local_desired_state(self, plugin_id: str) -> bool | None:
        config = getattr(self.plugin_manager, "config", None)
        if config and hasattr(config, "is_plugin_desired_enabled"):
            return bool(config.is_plugin_desired_enabled(plugin_id))
        return None

    async def start(self):
        """Start listening for state changes."""
        await self.bus.connect()
        
        # 1. Initial Sync (Snapshot)
        logger.info("♻️ Syncing initial plugin state from Bus...")
        initial_states = await self.bus.get_all_states()
        for plugin_id, state in initial_states.items():
            await self._handle_state_update(plugin_id, state)
            
        # 2. Subscribe to Live Updates
        await self.bus.subscribe_state(self._handle_state_update)
        logger.info("🎧 Listening for Plugin State updates...")

        # 3. [Architecture 30] Start Heartbeat Loop
        asyncio.create_task(self._heartbeat_loop())

    async def _heartbeat_loop(self):
        """Pulse every 5s to mark this worker as ALIVE"""
        worker_id = self.worker_id
        
        while True:
            try:
                # We use the Lifecycle Bus to update a 'worker' table or 'system_state'
                # For MVP, we'll assume the bus has a generic 'pulse' or we use 'update_state' 
                # on a pseudo-plugin ID representing the worker.
                # Or better: Add a specific method to LifecycleBus?
                # Let's use a "system.worker.X" pseudo-state for now.
                
                # Check if bus has a custom heartbeat method
                if hasattr(self.bus, "send_heartbeat"):
                    await self.bus.send_heartbeat(worker_id)
                else:
                    # Fallback: Log pulse (mock implementation until Bus upgrade)
                    # logger.debug(f"💓 Heartbeat: {worker_id}")
                    pass
                    
                await asyncio.sleep(5)
            except Exception as e:
                logger.error(f"Heartbeat Failed: {e}")
                await asyncio.sleep(10)

    async def _handle_state_update(self, plugin_id: str, state: Dict[str, Any]):
        """Callback for new state events"""
        # [P0 Fix] Filter by runtime_target - ignore plugins not meant for this Worker
        runtime_target = state.get("runtime_target")
        normalized_target = normalize_runtime_target(runtime_target)
        
        if self.expected_target:
            if not runtime_target:
                # [Defensive] Ignore updates without explicit target to avoid pollution
                # If a worker expects filtering, it shouldn't guess.
                return
                
            if normalized_target != self.expected_target:
                # This plugin belongs to a different worker, ignore
                return
        
        # [Architecture 6.0] Controller Pattern
        # Worker listens to 'desired_enabled' (Intent) ONLY - no fallback to 'enabled'
        desired = state.get("desired_enabled")
        
        if desired is None:
            # [P1 Fix] Strict mode: No fallback to 'enabled'
            # Old plugins without desired_enabled are ignored until migrated
            return

        local_desired = self._get_local_desired_state(plugin_id)
        if local_desired is not None and local_desired != desired:
            logger.info(
                f"🧭 Ignoring stale bus state for {plugin_id}: bus={desired}, config={local_desired}"
            )
            return

        if self._desired_state_cache.get(plugin_id) is desired:
            logger.debug(f"⏭️ Ignoring duplicate desired state for {plugin_id}: {desired}")
            return
            
        logger.info(f"⚡ [Bus] Control Signal: {plugin_id} -> Desired={desired}")
        
        try:
            if desired:
                # Enable Logic
                # In a Worker, "Enable" usually means: Load the Driver if applicable
                # We defer to the manager's logic.
                
                # Check if it's a driver we care about
                # For MVP, we just log. The Manager needs to support hot-loading.
                logger.info(f"🔄 Hot-Loading Plugin {plugin_id} (Worker Side)...")
                
                # If the manager has a 'load_plugin' or similar, call it.
                # Assuming standard SystemPluginManager interface or equivalent.
                # If the manager has a 'load_plugin' or similar, call it.
                # Assuming standard SystemPluginManager interface or equivalent.
                if hasattr(self.plugin_manager, "enable_plugin"):
                    await self.plugin_manager.enable_plugin(plugin_id)
                
            else:
                # Disable Logic
                logger.info(f"🛑 Unloading Plugin {plugin_id} (Worker Side)...")
                if hasattr(self.plugin_manager, "disable_plugin"):
                    await self.plugin_manager.disable_plugin(plugin_id)
            
            # [Fix] Force immediate status report
            if self.reporter:
                logger.info(f"⚡ Triggering Immediate Status Report for {plugin_id}...")
                asyncio.create_task(self.reporter.force_report())

            self._desired_state_cache[plugin_id] = desired
                    
        except Exception as e:
            logger.error(f"❌ Failed to sync state for {plugin_id}: {e}")
