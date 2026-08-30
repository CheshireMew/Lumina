
import logging
from typing import Callable, List, Dict, Any
from fastapi import FastAPI
from core.interfaces.capability import IWorkerCapability
from core.runtime import resolve_contract_url, runtime_target_for_capability
from .manager import VisionProviderManager

logger = logging.getLogger("VisionCapability")

class Capability(IWorkerCapability):
    def __init__(self):
        self.manager: VisionProviderManager | None = None

    @property
    def name(self) -> str:
        return "vision"

    def register_routes(self, app: FastAPI):
        from .routes import router as vision_router

        app.include_router(vision_router)

    def get_state_provider(self) -> Callable[[], List[Dict[str, Any]]]:
        return self._gather_vision_state

    def get_health_status(self) -> str:
        if self.manager is None or self.manager.active_driver is None:
            return "degraded"
        return "ok"

    def get_health_details(self) -> Dict[str, Any]:
        if self.manager is None:
            return {"providerStatus": "starting"}
        return {
            "providerStatus": "ready" if self.manager.active_driver is not None else "configuration_required",
            "provider": self.manager.active_driver_id,
            "error": self.manager.last_error,
        }

    async def on_startup(self, app: FastAPI):
        container = app.state.services
        from llm.manager import LLMManager

        llm_manager = LLMManager(container.get_config())
        container.set_llm_manager(llm_manager)

        def resolve_model_name(feature: str) -> str:
            return llm_manager.get_model_name(feature)

        manager = VisionProviderManager(
            config=container.get_config(),
            model_name_resolver=resolve_model_name,
            llm_manager=llm_manager,
        )
        await manager.register_drivers()
        self.manager = manager
        
        # 2. Register to Container
        container.set_vision(manager)
        
        logger.info(f"Vision Service Ready. Active Driver: {manager.active_driver_id}")

    async def on_shutdown(self):
        self.manager = None

    def _gather_vision_state(self) -> List[Dict[str, Any]]:
        from app_config import config
        from services.reporting.driver_state_collector import DriverStateCollector

        return DriverStateCollector.gather_driver_states(
            manager=self.manager,
            category="vision",
            runtime_target=runtime_target_for_capability("vision"),
            service_url=resolve_contract_url(config, "vision", "analyze"),
        )
