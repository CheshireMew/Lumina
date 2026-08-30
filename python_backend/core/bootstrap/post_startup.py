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

    async def _prewarm_workers(self, process_manager, capabilities):
        try:
            await asyncio.sleep(4)
            warm_targets = [
                asyncio.to_thread(
                    process_manager.start_worker,
                    runtime_target_for_capability(capability),
                )
                for capability in capabilities
            ]

            await asyncio.gather(*warm_targets)
            logger.info("🔥 Core worker prewarm dispatched")
        except Exception as e:
            logger.warning(f"Pre-warm task failed: {e}")
    
    async def bootstrap(self, container: Any):
        config = container.get_config()

        if not config.capabilities.prewarm_core:
            logger.debug("Prewarm disabled in config")
            return

        pm = container.get_process_manager()
        registry = pm.worker_runtime_registry
        capabilities = [
            capability
            for capability in registry.list_auto_start_capabilities()
            if registry.should_auto_start(capability)
        ]
        if not capabilities:
            logger.debug("Prewarm skipped: no worker runtime marked for auto start")
            return

        logger.info("🔥 Scheduling Core Service Prewarm (TTS/STT)...")
        container.set_prewarm_task(asyncio.create_task(
            self._prewarm_workers(pm, capabilities)
        ))


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
        from services.infra.config_watcher import ConfigWatcherService

        watcher = ConfigWatcherService(
            config_manager=container.get_config(),
            event_bus=container.get_event_bus(),
            worker_control_hub=container.get_worker_control_hub(),
        )
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


class WorkerControlHubBootstrapper(Bootstrapper):
    """
    Initialize Worker Control Hub for WebSocket communication.
    Manages bidirectional control channel with workers.
    """
    
    @property
    def name(self) -> str:
        return "WorkerControlHub"
    
    async def bootstrap(self, container: Any):
        from services.infra.service_discovery import ServiceDiscovery
        from services.infra.worker_control_hub import WorkerControlHub

        discovery = ServiceDiscovery()
        hub = WorkerControlHub(discovery)
        container.set_worker_discovery(discovery)
        container.set_worker_control_hub(hub)
        hub.start_cleanup_task()

        logger.info("🎛️ WorkerControlHub Ready")


class ProcessSupervisorBootstrapper(Bootstrapper):
    """
    Start Process Supervisor for auto-healing.
    """
    
    @property
    def name(self) -> str:
        return "ProcessSupervisor"
    
    async def bootstrap(self, container: Any):
        config = container.get_config()
        if not config.capabilities.supervise_workers:
            logger.debug("Process supervisor disabled in config")
            return

        pm = container.get_process_manager()
        await pm.start_supervisor()
        logger.info("🛡️ Process Supervisor Auto-Healing Enabled")
