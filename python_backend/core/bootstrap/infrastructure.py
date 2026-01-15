
import os
import sys
import logging
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Infra")

class ConfigBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Configuration"

    async def bootstrap(self, container):
        from app_config import ConfigManager, BASE_DIR
        cm = ConfigManager()
        container.config = cm
        
        # Character Resolve Logic
        character_id = cm.memory.character_id or "hiyori"
        
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
                    character_id = "lumina_default"
        
        # Stash resolved character_id in config for downstream access if needed,
        # or just rely on container injection later.
        # Ideally ConfigManager should handle this, but for now we patch it.
        cm.memory.character_id = character_id
        logger.info(f"✅ Config Loaded for: {character_id}")


class DatabaseBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "SurrealDB"

    async def bootstrap(self, container):
        from memory.core import SurrealMemory
        from model_manager import model_manager
        from app_config import config
        from consolidation_batch import BatchManager
        
        character_id = container.config.memory.character_id
        
        # Load Embedding
        model_subpath = "all-MiniLM-L6-v2"
        embedding_model = None
        try:
             path = model_manager.ensure_embedding_model(model_subpath)
             embedding_model = model_manager.load_embedding_model(str(path))
        except Exception as e:
             logger.error(f"Embedding load failed: {e}")

        # Connect
        try:
            surreal = SurrealMemory(character_id=character_id)
            if embedding_model:
                surreal.set_encoder(embedding_model.encode)
            
            await surreal.connect()
            
            # Batch Manager
            batch_mgr = BatchManager()
            container.batch_manager = batch_mgr
            surreal.set_batch_manager(batch_mgr)
            
            container.surreal_system = surreal
            logger.info("✅ SurrealDB Connected")
            
        except Exception as e:
            logger.critical(f"SurrealDB Failed: {e}")
            sys.exit(1)


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
        gateway_service.bus = bus
        gateway_service._subscribe_all()
        container.gateway = gateway_service # Note: container uses set_gateway logic usually
        
        # Schemas
        bus.register_schema("system.ready", EventSchema("1.0", SystemReadyPayload))
        bus.register_schema("system.shutdown", EventSchema("1.0", SystemShutdownPayload))
        bus.register_schema("plugin.loaded", EventSchema("1.0", PluginLoadedPayload))
        bus.register_schema("plugin.error", EventSchema("1.0", PluginErrorPayload))
