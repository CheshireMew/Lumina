
import asyncio
import logging
import os
from pathlib import Path
from typing import Optional, Callable, List
from app_config import config, CONFIG_ROOT
from core.interfaces.configurable import IConfigurable


logger = logging.getLogger("ConfigWatcher")

class ConfigWatcherService:
    """
    [Architecture 5.6] Configuration Watcher Service.
    Monitors config.yaml for manual changes and triggers reloads.
    
    Can be used in Main or Worker processes.
    """
    def __init__(self, interval: float = 2.0):
        self.interval = interval
        self.config_path = CONFIG_ROOT / "config.yaml"
        self._last_mtime: Optional[float] = None
        self._running = False
        self._callbacks: List[Callable[[], None]] = []
        self._configurables: List[IConfigurable] = []
        
        # Initialize mtime
        if self.config_path.exists():
            self._last_mtime = os.path.getmtime(self.config_path)

    def on_change(self, callback: Callable[[], None]):
        """Register a callback to be executed when config changes."""
        self._callbacks.append(callback)

    def register_configurable(self, configurable: IConfigurable):
        """Register an IConfigurable instance for updates."""
        if configurable not in self._configurables:
            self._configurables.append(configurable)


    async def start(self):
        """Start the polling loop."""
        if self._running:
            return
        
        self._running = True
        logger.info(f"👀 ConfigWatcher started. Monitoring: {self.config_path}")
        
        while self._running:
            try:
                await self._check_for_changes()
            except Exception as e:
                logger.error(f"Error checking config for changes: {e}")
            
            await asyncio.sleep(self.interval)

    def stop(self):
        """Stop the polling loop."""
        self._running = False
        logger.info("🛑 ConfigWatcher stopped.")

    async def _check_for_changes(self):
        if not self.config_path.exists():
            return

        current_mtime = os.path.getmtime(self.config_path)
        
        if self._last_mtime is None:
            self._last_mtime = current_mtime
            return

        if current_mtime > self._last_mtime:
            logger.info("🔄 Config file change detected! Reloading units...")
            self._last_mtime = current_mtime
            
            # 1. Reload Config Singleton
            config.reload()
            
            # 2. Trigger Callbacks
            for cb in self._callbacks:
                try:
                    if asyncio.iscoroutinefunction(cb):
                        await cb()
                    else:
                        cb()
                except Exception as e:
                    logger.error(f"Error in ConfigWatcher callback: {e}")
            
            # 2.5 Notify IConfigurables
            config_dump = config._plugins_config.model_dump() # Or full config?
            # Ideally pass the whole config context or let them pull
            # IConfigurable.on_config_update(data)
            # For now, we trigger them. They can pull from 'config' singleton or we pass data.
            # Let's pass a dict representation of the new config.
            # Note: app_config.config is already reloaded.
            
            # Construct a safe dict to pass
            full_config_data = {
                "llm": config.llm.model_dump(),
                "stt": config.stt.model_dump(),
                "tts": config.tts.model_dump(),
                "plugins": config.plugins.model_dump()
            }
            
            for conf in self._configurables:
                try:
                    conf.on_config_update(full_config_data)
                except Exception as e:
                    logger.error(f"Error updating configurable {conf}: {e}")
            
            # 3. Emit Global Event (if bus exists)
            try:
                from core.events.bus import bus
                await bus.emit("system.config_reloaded", {"path": str(self.config_path)})
            except ImportError:
                pass
            except Exception as e:
                logger.debug(f"Could not emit global config event: {e}")
            
            # 4. Broadcast to Workers via WebSocket (Main Process only)
            try:
                from services.infra.worker_control_hub import get_worker_control_hub
                hub = get_worker_control_hub()
                
                # Only broadcast if we have connected workers
                workers = hub.get_all_workers()
                if workers:
                    await hub.broadcast_config_update(data={"reload": True}, section=None)
                    logger.info(f"📢 Config update broadcasted to {len(workers)} workers via WebSocket")
            except Exception as e:
                # Not in Main Process or hub not available - that's fine
                logger.debug(f"WebSocket broadcast skipped: {e}")

