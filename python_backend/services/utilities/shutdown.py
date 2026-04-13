"""
Shutdown Manager.
Centralized orchestration of graceful service termination.
"""

import logging
from typing import Any
from fastapi import FastAPI

logger = logging.getLogger("ShutdownManager")


class ShutdownManager:
    """
    Manages graceful shutdown of all services in correct order.
    
    Shutdown Order (reverse of startup):
    1. MCP Host (external integrations)
    2. Config Watcher (monitoring)
    3. Reconciliation Service (sync)
    4. System Plugins (extensions)
    5. Ticker (background tasks)
    6. Worker Control Hub (IPC)
    7. Process Manager (child processes)
    8. Database (persistence)
    """
    
    async def shutdown(self, container: Any, app: FastAPI = None) -> None:
        """
        Execute graceful shutdown sequence.
        
        Args:
            container: ServiceContainer instance
            app: FastAPI application instance (optional)
        """
        logger.info("🛑 Starting graceful shutdown...")
        
        # 1. MCP Host
        await self._stop_mcp_host(container)
        
        # 2. Config Watcher
        self._stop_config_watcher(container)
        
        # 3. Reconciliation Service
        await self._stop_reconciliation(container)
        
        # 4. System Plugins
        await self._stop_system_plugins(container)
        
        # 5. Ticker
        self._stop_ticker(container)
        
        # 6. Pending startup tasks
        await self._stop_prewarm_task(container)
        
        # 7. Worker Control Hub
        await self._stop_worker_control_hub()
        
        # 8. Process Manager
        await self._stop_process_manager(container)
        
        # 9. Database
        await self._stop_database(container)
        
        logger.info("✅ Shutdown complete")
    
    async def _stop_mcp_host(self, container: Any):
        if container.mcp_host:
            logger.info("Stopping MCP Host...")
            try:
                await container.mcp_host.stop()
            except Exception as e:
                logger.error(f"Error stopping MCP Host: {e}")
    
    def _stop_config_watcher(self, container: Any):
        watcher = container.get_config_watcher()
        if watcher:
            logger.info("Stopping ConfigWatcher...")
            watcher.stop()
    
    async def _stop_reconciliation(self, container: Any):
        import asyncio
        reconciler = container.get_reconciliation_service()
        if reconciler:
            logger.info("Stopping Reconciliation Service...")
            try:
                await reconciler.stop()
            except asyncio.CancelledError:
                logger.warning("Reconciliation stop was cancelled (acceptable)")
            except Exception as e:
                logger.error(f"Error stopping Reconciliation: {e}")
    
    async def _stop_system_plugins(self, container: Any):
        if container.system_plugin_manager:
            logger.info("Stopping System Plugins...")
            try:
                await container.system_plugin_manager.shutdown()
            except Exception as e:
                logger.error(f"Error stopping unified plugin kernel: {e}")
    
    def _stop_ticker(self, container: Any):
        if container.ticker:
            logger.info("Stopping Ticker...")
            container.ticker.stop()

    async def _stop_prewarm_task(self, container: Any):
        import asyncio

        task = getattr(container, "prewarm_task", None)
        if not task:
            return
        if task.done():
            return
        logger.info("Cancelling worker prewarm task...")
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            logger.debug("Worker prewarm task cancelled")
        except Exception as e:
            logger.debug(f"Worker prewarm task shutdown: {e}")
    
    async def _stop_worker_control_hub(self):
        try:
            from services.infra.worker_control_hub import get_worker_control_hub
            hub = get_worker_control_hub()
            await hub.shutdown()
        except Exception as e:
            logger.debug(f"WorkerControlHub shutdown: {e}")
    
    async def _stop_process_manager(self, container: Any):
        import asyncio
        pm = container.get_process_manager()
        if pm:
            logger.info("Stopping Process Manager...")
            try:
                await pm.shutdown_all()
            except asyncio.CancelledError:
                logger.warning("ProcessManager stop was cancelled")
            except Exception as e:
                logger.error(f"Error stopping ProcessManager: {e}")
    
    async def _stop_database(self, container: Any):
        # Use try/except because get_memory raises if not initialized
        try:
            mem = container.get_memory()
            if mem:
                logger.info("Closing Database connection...")
                # Assuming IMemoryService or driver has close() properly exposed
                # If memory service is a facade, it might delegate close.
                # If it's the raw driver, it has close.
                # Let's check if it has close method.
                if hasattr(mem, "close"):
                    await mem.close()
        except Exception:
            # Not initialized or already closed
            pass
