
import os
import logging
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Infra")

class ConfigBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Configuration"

    async def bootstrap(self, container):
        from app_config import BASE_DIR, config
        container.set_config(config)
        
        # Character Resolve Logic
        character_id = config.memory.character_id or "hiyori"
        
        # Verify Character Directory
        base_char_dir = os.path.join(str(BASE_DIR), "characters")
        target_dir = os.path.join(base_char_dir, character_id)
        
        if not os.path.exists(target_dir):
            logger.warning(f"Configured character '{character_id}' not found.")
            if os.path.exists(base_char_dir):
                found = [d for d in os.listdir(base_char_dir) if os.path.isdir(os.path.join(base_char_dir, d))]
                if found:
                    character_id = 'lillian' if 'lillian' in found else found[0]
                    logger.info(f"Fallback to: {character_id}")
                else:
                    # [Fix] Verify 'lumina_default' exists before falling back blind
                    default_path = os.path.join(base_char_dir, "lumina_default")
                    if os.path.exists(default_path):
                        character_id = "lumina_default"
                    else:
                        logger.critical(f"Panic: No characters found in {base_char_dir}. Please install a character.")
                        # sys.exit(1) # Optional: hard fail or allow boot empty? Allow boot for setup UI.
                        character_id = "setup_required"
        
        # Stash resolved character_id in config for downstream access if needed,
        # or just rely on container injection later.
        # Ideally ConfigManager should handle this, but for now we patch it.
        config.memory.character_id = character_id
        logger.info(f"✅ Config Loaded for: {character_id}")


class DatabaseBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Memory Backend"

    async def bootstrap(self, container):
        from memory.core import MemoryService
        from memory.factory import NoOpDriver
        from model_manager import model_manager
        from consolidation_batch import BatchManager
        
        character_id = container.config.memory.character_id
        
        memory_svc = MemoryService(character_id=character_id)
        memory_svc.set_encoder(
            model_manager.create_lazy_embedding_encoder("all-MiniLM-L6-v2")
        )

        batch_mgr = BatchManager()
        container.batch_manager = batch_mgr
        memory_svc.set_batch_manager(batch_mgr)

        try:
            await memory_svc.connect()
            memory_svc.set_available(True)
            logger.info("✅ Memory System Connected")
        except Exception as e:
            logger.error(f"Memory backend unavailable, continuing in degraded mode: {e}")
            memory_svc.set_driver(NoOpDriver())
            memory_svc.set_available(False, str(e))

        container.set_memory(memory_svc)


class EventBusBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "EventBus"

    async def bootstrap(self, container):
        from core.events import init_event_bus
        from routers.gateway import gateway_service
        from core.events.definitions import SystemReadyPayload, SystemShutdownPayload, PluginLoadedPayload, PluginErrorPayload
        from core.events.bus import EventSchema
        
        bus = init_event_bus()
        container.event_bus = bus
        logger.info("✅ EventBus Initialized")
        
        # Bind Gateway
        # [FIX] Do NOT call _subscribe_all() again - it's already called in GatewayService.__init__()
        # Calling it twice causes duplicate subscriptions and double WebSocket broadcasts!
        gateway_service.bus = bus
        # gateway_service._subscribe_all()  # REMOVED: Causes duplicate event handlers
        container.gateway = gateway_service
        
        # Schemas
        bus.register_schema("system.ready", EventSchema("1.0", SystemReadyPayload))
        bus.register_schema("system.shutdown", EventSchema("1.0", SystemShutdownPayload))
        bus.register_schema("plugin.loaded", EventSchema("1.0", PluginLoadedPayload))
        bus.register_schema("plugin.error", EventSchema("1.0", PluginErrorPayload))

class ProtocolBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Event Protocol (Schemas)"

    async def bootstrap(self, container):
        if not container.event_bus:
            logger.warning("EventBus not found, skipping protocol registration.")
            return
            
        from core.protocol import CORE_SCHEMAS
        container.event_bus.bulk_register_schemas(CORE_SCHEMAS)
        logger.info(f"✅ Protocol Schema Validation Active ({len(CORE_SCHEMAS)} events)")
