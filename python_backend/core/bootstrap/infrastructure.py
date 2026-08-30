
import logging
from pathlib import Path
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Infra")

class ConfigBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Configuration"

    async def bootstrap(self, container):
        from app_config import BASE_DIR, DATA_ROOT, config
        container.set_config(config)
        
        character_id = str(config.memory.character_id or "").strip()
        if not character_id:
            raise ValueError("memory.character_id must be configured")

        character_roots = (
            Path(DATA_ROOT) / "characters",
            Path(BASE_DIR) / "characters",
        )
        if not any((root / character_id).exists() for root in character_roots):
            searched = ", ".join(str(root / character_id) for root in character_roots)
            raise FileNotFoundError(f"Configured character not found. Searched: {searched}")

        logger.info(f"✅ Config Loaded for: {character_id}")


class WorkerRuntimeRegistryBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Worker Runtime Registry"

    async def bootstrap(self, container):
        from core.worker_runtimes import WorkerRuntimeRegistry

        container.set_worker_runtime_registry(WorkerRuntimeRegistry())
        logger.info("✅ Worker Runtime Registry Initialized")


class DatabaseBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Memory Backend"

    async def bootstrap(self, container):
        from app_config import DATA_ROOT
        from memory.core import MemoryService
        from memory.factory import MemoryDriverFactory
        from services.local_embedding import (
            DEFAULT_EMBEDDING_MODEL,
            create_semantic_encoder,
        )
        
        config = container.get_config()
        provider_id = config.get_selected_provider("memory")
        if not provider_id:
            raise ValueError("No memory provider selected in configuration.")
        
        driver = MemoryDriverFactory.create_driver(
            provider_id,
            driver_config={
                **config.memory.model_dump(),
                "data_root": str(getattr(config, "data_root", DATA_ROOT)),
            },
        )
        memory_svc = MemoryService(driver=driver)
        embedding_model_name = config.models.embedding_model_name
        if embedding_model_name.lower().startswith("text-embedding-"):
            logger.warning(
                "Configured embedding model %s is a remote API model name; using local model %s",
                embedding_model_name,
                DEFAULT_EMBEDDING_MODEL,
            )
            embedding_model_name = DEFAULT_EMBEDDING_MODEL
        memory_svc.set_encoder(
            create_semantic_encoder(embedding_model_name),
            model_name=embedding_model_name,
        )

        await memory_svc.connect()
        logger.info("✅ Memory System Connected")
        container.set_memory(memory_svc)


class EventBusBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "EventBus"

    async def bootstrap(self, container):
        from core.events import EventBus
        from routers.gateway import GatewayService
        from core.events.definitions import (
            SystemReadyPayload,
            SystemShutdownPayload,
        )
        from core.events.bus import EventSchema
        
        bus = EventBus()
        container.set_event_bus(bus)
        logger.info("✅ EventBus Initialized")
        
        # Bind Gateway
        # [FIX] Do NOT call _subscribe_all() again - it's already called in GatewayService.__init__()
        # Calling it twice causes duplicate subscriptions and double WebSocket broadcasts!
        gateway_service = GatewayService(bus)
        container.set_gateway(gateway_service)
        
        # Schemas
        bus.register_schema("system.ready", EventSchema("1.0", SystemReadyPayload))
        bus.register_schema("system.shutdown", EventSchema("1.0", SystemShutdownPayload))

class ProtocolBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Event Protocol (Schemas)"

    async def bootstrap(self, container):
        from core.protocol import CORE_SCHEMAS
        container.get_event_bus().bulk_register_schemas(CORE_SCHEMAS)
        logger.info(f"✅ Protocol Schema Validation Active ({len(CORE_SCHEMAS)} events)")
