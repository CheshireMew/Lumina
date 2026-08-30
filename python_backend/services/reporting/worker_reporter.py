import asyncio
import logging
from typing import Callable, List, Dict, Any
from core.schemas import WorkerState

logger = logging.getLogger("WorkerReporter")

class WorkerStatusReporter:
    """
    Reports worker health to Lumina's local lifecycle store.
    """
    def __init__(self, 
                 worker_id: str, 
                 state_provider: Callable[[], List[Dict[str, Any]]],
                 interval: int = 90,
                 host: str = "127.0.0.1",
                 port: int = None):
        
        self.worker_id = worker_id
        self.state_provider = state_provider
        self.interval = interval
        self.host = host
        self.port = port
        self._running = False
        self._task = None
        
        # [Architecture 6.1] Bus Integration
        from services.infra.bus_factory import get_lifecycle_bus
        self.bus = get_lifecycle_bus()

    def start(self):
        if not self._running:
            self._running = True
            logger.info(f"📡 Status Reporter (Mesh Mode) started for {self.worker_id}")
            self._task = asyncio.create_task(self._report_loop())

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
            if self.bus:
                await self.bus.disconnect()
            logger.info("Status Reporter stopped.")

    async def _report_loop(self):
        # Initial delay to allow DB startup
        await asyncio.sleep(5)
        
        while self._running:
            try:
                if not self.bus.is_connected:
                    await self.bus.connect()

                # 1. Report Worker State
                w_state = WorkerState(
                    worker_id=self.worker_id,
                    host=self.host,
                    port=self.port,
                    status="healthy",
                    load=self._get_system_load()
                )
                await self.bus.update_worker_state(w_state)

            except Exception as e:
                logger.error(f"Reporter Error: {e}")
            
            await asyncio.sleep(self.interval)

    def _get_system_load(self) -> float:
        """
        Calculate system load (0.0 - 1.0).
        Uses psutil if available, otherwise returns simulated low load.
        """
        try:
            import psutil
            cpu = psutil.cpu_percent(interval=None) / 100.0
            mem = psutil.virtual_memory().percent / 100.0
            return max(cpu, mem)
        except ImportError:
            # Fallback for environments without psutil
            return 0.1
        except Exception as e:
            logger.warning(f"Failed to get system load: {e}")
            return 0.0

    async def force_report(self):
        """
        Manually trigger a report immediately.
        """
        try:
            if not self.bus.is_connected:
                await self.bus.connect()
                
            await self.bus.update_worker_state(
                WorkerState(
                    worker_id=self.worker_id,
                    host=self.host,
                    port=self.port,
                    status="healthy",
                    load=self._get_system_load(),
                )
            )
            logger.info("⚡ Forced Worker Status Push Sent.")
                    
        except Exception as e:
            logger.error(f"Force Report Failed: {e}")
