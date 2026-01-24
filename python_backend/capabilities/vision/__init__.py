
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from services.container import services
from .manager import VisionPluginManager
from .routes import router as vision_router

logger = logging.getLogger("VisionCapability")

class Capability(IWorkerCapability):
    @property
    def name(self) -> str:
        return "vision"

    def register_routes(self, app: FastAPI):
        # Mount with prefix is done by Generic Worker typically, or we define it here.
        # Original router had prefix="/lumina/vision".
        # Let's keep it under /vision for cleaner API or respect original.
        # But generic worker usually maps root or convention.
        # Let's just include the router. Routes within are /analyze, /load, etc.
        app.include_router(vision_router)

    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        # Minimal state reporting for now
        return lambda: [{"id": "vision_service", "status": "active"}]

    async def on_startup(self, app: FastAPI):
        # 1. Initialize Manager
        manager = VisionPluginManager()
        await manager.register_drivers()
        
        # 2. Register to Container
        services.register_vision(manager)
        
        logger.info(f"Vision Service Ready. Active Driver: {manager.active_driver_id}")

    async def on_shutdown(self):
        # Cleanup if needed
        pass
