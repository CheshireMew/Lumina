
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from services.container import services
from .manager import MemoryPluginManager
from .routes import router as memory_router
from . import globals as memory_globals

logger = logging.getLogger("MemoryCapability")

class Capability(IWorkerCapability):
    @property
    def name(self) -> str:
        return "memory"

    def register_routes(self, app: FastAPI):
        # Mount routes. Usually /memory prefix is desired if adhering to old Main.py structure
        # But generic worker routes are usually top-level for that worker.
        # Main.py uses gateway to Proxy to /memory? Or just calls it?
        # If we mount as /memory, then access is localhost:PORT/memory/add
        # If we mount as /, then access is localhost:PORT/add
        # To match main.py's `app.include_router(memory.router, prefix="/memory")`, we should prefix here too?
        # NO. Routers usually define their own paths or we wrap.
        # `capabilities/memory/routes.py` has `@router.post("/add")`.
        # So we probably want `app.include_router(memory_router, prefix="/memory")` to match old API structure strictly
        # IF the frontend/clients expect `/memory/add`.
        # Let's verify `routers/memory.py` had no prefix in APIRouter(tags), but `main.py` included it with prefix="/memory".
        # So we MUST include prefix="/memory" here or inside routes.
        app.include_router(memory_router, prefix="/memory")

    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        return lambda: [{"id": "memory", "status": self.manager.status if hasattr(self, 'manager') else "unknown"}]

    async def on_startup(self, app: FastAPI):
        # 1. Initialize Manager
        self.manager = MemoryPluginManager()
        await self.manager.initialize()
        
        # 2. Register to Container (So Deps work)
        # Note: In Generic Worker process, services.register_memory(self.manager) 
        # makes get_memory_service() return THIS manager.
        services.register_memory(self.manager)
        
        logger.info(f"Memory Service Ready.")

    async def on_shutdown(self):
        if hasattr(self, 'manager'):
            await self.manager.shutdown()
