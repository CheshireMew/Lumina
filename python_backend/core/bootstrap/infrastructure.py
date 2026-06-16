
import logging
from pathlib import Path
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Infra")

class ConfigBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Configuration"

    async def bootstrap(self, container):
        from app_config import BASE_DIR, config
        container.set_config(config)
        
        character_id = str(config.memory.character_id or "").strip()
        if not character_id:
            raise ValueError("memory.character_id must be configured")

        base_char_dir = Path(BASE_DIR) / "characters"
        target_dir = base_char_dir / character_id

        if not target_dir.exists():
            raise FileNotFoundError(f"Configured character not found: {target_dir}")

        logger.info(f"✅ Config Loaded for: {character_id}")


class DatabaseBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Memory Backend"

    async def bootstrap(self, container):
        from memory.core import MemoryService
        from memory.factory import MemoryDriverFactory
        from model_manager import model_manager
        from consolidation_batch import BatchManager
        
        config = container.get_config()
        character_id = config.memory.character_id
        provider_id = config.get_selected_provider("memory")
        if not provider_id:
            raise ValueError("No memory provider selected in configuration.")
        
        driver = MemoryDriverFactory.create_driver(
            provider_id,
            driver_config=config.memory.model_dump(),
        )
        memory_svc = MemoryService(driver=driver, character_id=character_id)
        package_registry = container.get_capability_package_registry()
        vision_snapshot = package_registry.resolve("vision-runtime") if package_registry else None
        if vision_snapshot and vision_snapshot.status == "ready":
            memory_svc.set_encoder(
                model_manager.create_lazy_embedding_encoder("all-MiniLM-L6-v2")
            )
        else:
            logger.info("Vision runtime unavailable. Memory retrieval will use full-text fallback.")

        batch_mgr = BatchManager()
        container.set_batch_manager(batch_mgr)
        memory_svc.set_batch_manager(batch_mgr)

        try:
            await memory_svc.connect()
            memory_svc.set_available(True)
            logger.info("✅ Memory System Connected")
        except Exception as e:
            logger.error(f"Memory backend unavailable, continuing in degraded mode: {e}")
            memory_svc.set_available(False, str(e))

        container.set_memory(memory_svc)


class EventBusBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "EventBus"

    async def bootstrap(self, container):
        from core.events import init_event_bus
        from routers.gateway import gateway_service
        from core.events.definitions import (
            SystemReadyPayload,
            SystemShutdownPayload,
            PluginLifecycleRequest,
            PluginLoadedPayload,
            PluginDisabledPayload,
            PluginErrorPayload,
        )
        from core.events.bus import EventSchema
        
        bus = init_event_bus()
        container.set_event_bus(bus)
        logger.info("✅ EventBus Initialized")
        
        # Bind Gateway
        # [FIX] Do NOT call _subscribe_all() again - it's already called in GatewayService.__init__()
        # Calling it twice causes duplicate subscriptions and double WebSocket broadcasts!
        gateway_service.bus = bus
        # gateway_service._subscribe_all()  # REMOVED: Causes duplicate event handlers
        container.set_gateway(gateway_service)
        
        # Schemas
        bus.register_schema("system.ready", EventSchema("1.0", SystemReadyPayload))
        bus.register_schema("system.shutdown", EventSchema("1.0", SystemShutdownPayload))
        bus.register_schema("plugin.lifecycle.request_enable", EventSchema("1.0", PluginLifecycleRequest))
        bus.register_schema("plugin.lifecycle.request_disable", EventSchema("1.0", PluginLifecycleRequest))
        bus.register_schema("plugin.loaded", EventSchema("1.0", PluginLoadedPayload))
        bus.register_schema("plugin.disabled", EventSchema("1.0", PluginDisabledPayload))
        bus.register_schema("plugin.error", EventSchema("1.0", PluginErrorPayload))

class ProtocolBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Event Protocol (Schemas)"

    async def bootstrap(self, container):
        if not container.has_service("event_bus"):
            logger.warning("EventBus not found, skipping protocol registration.")
            return
            
        from core.protocol import CORE_SCHEMAS
        container.get_event_bus().bulk_register_schemas(CORE_SCHEMAS)
        logger.info(f"✅ Protocol Schema Validation Active ({len(CORE_SCHEMAS)} events)")
