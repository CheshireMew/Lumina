"""
Post-Startup Bootstrappers.
Services that initialize after core services are ready.
"""

import asyncio
import logging
from typing import Any
from fastapi import FastAPI
from .interface import Bootstrapper
from core.runtime import runtime_target_for_capability

logger = logging.getLogger("Bootstrap.PostStartup")


class PrewarmBootstrapper(Bootstrapper):
    """
    Pre-warm core worker services (TTS/STT).
    Starts worker processes early to reduce first-request latency.
    """
    
    @property
    def name(self) -> str:
        return "Prewarm"

    async def _prewarm_workers(self, process_manager):
        try:
            await asyncio.sleep(4)
            await asyncio.gather(
                asyncio.to_thread(process_manager.start_worker, runtime_target_for_capability("tts")),
                asyncio.to_thread(process_manager.start_worker, runtime_target_for_capability("stt")),
            )
            logger.info("🔥 Core worker prewarm dispatched")
        except Exception as e:
            logger.warning(f"Pre-warm task failed: {e}")
    
    async def bootstrap(self, container: Any):
        try:
            from app_config import config
            
            if not config.plugins.prewarm_core:
                logger.debug("Prewarm disabled in config")
                return
            
            pm = container.get_process_manager()
            if not pm:
                logger.debug("Prewarm skipped: No ProcessManager")
                return
            
            logger.info("🔥 Scheduling Core Service Prewarm (TTS/STT)...")
            container.prewarm_task = asyncio.create_task(
                self._prewarm_workers(pm)
            )
            
        except Exception as e:
            logger.warning(f"Pre-warm failed: {e}")


class ReconciliationBootstrapper(Bootstrapper):
    """
    Start Reconciliation Service for state consistency.
    Ensures Worker and Main Process states remain synchronized.
    """
    
    @property
    def name(self) -> str:
        return "ReconciliationService"
    
    async def bootstrap(self, container: Any):
        try:
            from services.utilities.reconciliation import ReconciliationService
            
            reconciler = ReconciliationService(container)
            container.register_reconciliation_service(reconciler)
            reconciler.start()
            logger.info("⚖️ Reconciliation Service Started")
            
        except Exception as e:
            logger.error(f"Failed to start ReconciliationService: {e}")


class ConfigWatcherBootstrapper(Bootstrapper):
    """
    Start ConfigWatcher service.
    Monitors config.yaml for changes and triggers reloads.
    """
    
    def __init__(self, app: FastAPI = None):
        self._app = app
    
    @property
    def name(self) -> str:
        return "ConfigWatcher"
    
    async def bootstrap(self, container: Any):
        try:
            from services.infra.config_watcher import ConfigWatcherService
            
            watcher = ConfigWatcherService()
            container.set_config_watcher(watcher)
            
            # Register callback for physical config changes
            async def on_config_physical_change():
                logger.info("📢 [Watcher] Physical config change detected")
                # WebSocket broadcast is handled inside ConfigWatcherService
            
            watcher.on_change(on_config_physical_change)
            
            # Start background loop
            if self._app:
                self._app.state.config_watcher_task = asyncio.create_task(watcher.start())
            else:
                asyncio.create_task(watcher.start())
            
            logger.info("👀 ConfigWatcher Started")
            
        except Exception as e:
            logger.error(f"Failed to start ConfigWatcher: {e}")


class WorkerControlHubBootstrapper(Bootstrapper):
    """
    Initialize Worker Control Hub for WebSocket communication.
    Manages bidirectional control channel with workers.
    """
    
    @property
    def name(self) -> str:
        return "WorkerControlHub"
    
    async def bootstrap(self, container: Any):
        try:
            from services.infra.worker_control_hub import get_worker_control_hub
            
            hub = get_worker_control_hub()
            hub.start_cleanup_task()

            # Initialize PluginStateAggregator (unified state view for frontend)
            from services.plugin_state_aggregator import init_plugin_state_aggregator
            aggregator = await init_plugin_state_aggregator(container.event_bus)
            container.plugin_state_aggregator = aggregator

            # Seed with existing local plugin states (SystemPlugins loaded at Level 3)
            spm = getattr(container, 'system_plugin_manager', None)
            if spm:
                await aggregator.bulk_update(spm.list_plugins(), source="local")

            logger.info("🎛️ WorkerControlHub Ready")
            
        except Exception as e:
            logger.warning(f"WorkerControlHub init failed: {e}")


class ProcessSupervisorBootstrapper(Bootstrapper):
    """
    Start Process Supervisor for auto-healing.
    """
    
    @property
    def name(self) -> str:
        return "ProcessSupervisor"
    
    async def bootstrap(self, container: Any):
        try:
            pm = container.get_process_manager()
            if pm:
                await pm.start_supervisor()
                logger.info("🛡️ Process Supervisor Auto-Healing Enabled")
            else:
                logger.warning("Process Supervisor skipped: No PM")
                
        except Exception as e:
            logger.error(f"Failed to start Process Supervisor: {e}")


class AutomationBootstrapper(Bootstrapper):
    """
    Start Automation Service (ECA Engine).
    Phase: Core.
    """
    @property
    def name(self) -> str: return "AutomationService"

    async def bootstrap(self, container: Any):
        try:
            from services.automation.service import AutomationService
            
            # Instantiate
            auto_service = AutomationService(container)
            
            # Register in container
            container.set_automation_service(auto_service)
            
            # Start
            auto_service.start()
            
        except Exception as e:
            logger.error(f"Failed to start Automation Service: {e}")
