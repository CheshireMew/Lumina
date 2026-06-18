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
    1. Config Watcher (monitoring)
    2. Built-in middleware services
    3. Ticker (background tasks)
    4. Worker Control Hub (IPC)
    5. Process Manager (child processes)
    6. Database (persistence)
    """
    
    async def shutdown(self, container: Any, app: FastAPI = None) -> None:
        """
        Execute graceful shutdown sequence.
        
        Args:
            container: ServiceContainer instance
            app: FastAPI application instance (optional)
        """
        logger.info("🛑 Starting graceful shutdown...")
        
        # 1. Config Watcher
        self._stop_config_watcher(container)
        
        # 2. Built-in middleware services
        await self._stop_emotion_broker(container)
        
        # 3. Ticker
        self._stop_ticker(container)
        
        # 4. Pending startup tasks
        await self._stop_prewarm_task(container)
        
        # 5. Worker Control Hub
        await self._stop_worker_control_hub()
        
        # 6. Process Manager
        await self._stop_process_manager(container)
        
        # 7. Database
        await self._stop_database(container)
        
        logger.info("✅ Shutdown complete")
    
    def _stop_config_watcher(self, container: Any):
        watcher = container.get_config_watcher()
        if watcher:
            logger.info("Stopping ConfigWatcher...")
            watcher.stop()
    
    async def _stop_emotion_broker(self, container: Any):
        if not container.has_service("emotion_broker"):
            return

        emotion_broker = container.get_emotion_broker()
        logger.info("Stopping EmotionBroker...")
        try:
            await emotion_broker.stop()
        except Exception as e:
            logger.error(f"Error stopping EmotionBroker: {e}")
    
    def _stop_ticker(self, container: Any):
        ticker = container.get_ticker()
        if ticker:
            logger.info("Stopping Ticker...")
            ticker.stop()

    async def _stop_prewarm_task(self, container: Any):
        import asyncio

        task = container.get_prewarm_task()
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
