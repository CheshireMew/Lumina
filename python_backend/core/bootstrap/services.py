
import logging
from .interface import Bootstrapper
from core.runtime import resolve_runtime_port, runtime_target_for_capability

logger = logging.getLogger("Bootstrap.Services")

class CoreServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Core Services"

    async def bootstrap(self, container):
        from services.process_manager import ProcessManager
        from services.capability_registry import CapabilityRegistry
        from services.character_service import CharacterService
        # from app_config import config # Global import removed
        pm = ProcessManager()
        
        # [Architecture 5.0] Register Core Services
        config = container.config
        pm.register_service_def(
            runtime_target_for_capability("stt"),
            config.network.stt_port,
            "backend_launcher.py",
            ["worker", "--capability", "stt"],
        )
        pm.register_service_def(
            runtime_target_for_capability("tts"),
            config.network.tts_port,
            "backend_launcher.py",
            ["worker", "--capability", "tts"],
        )
        pm.register_service_def(
            runtime_target_for_capability("vision"),
            resolve_runtime_port(config, runtime_target_for_capability("vision")) or 8005,
            "backend_launcher.py",
            ["worker", "--capability", "vision"],
        )
        
        container.set_process_manager(pm)
        container.capability_registry = CapabilityRegistry()
        container.character_service = CharacterService()

        # 1. LLM
        from llm.manager import LLMManager
        container.llm_manager = LLMManager()
        
        # 2. Soul (Service)
        from services.orchestrators.soul import SoulService
        container.soul = SoulService(
            system_config=container.config,
            memory_service=container.get_memory(),
        )
        
        # 3. Session
        from services.orchestrators.session import SessionManager
        container.session_manager = SessionManager(config=container.config)

        from services.chat.pipeline import ChatPipeline
        from services.chat.service import ChatTurnService

        chat_pipeline = ChatPipeline(container)
        container.set_chat_pipeline(chat_pipeline)
        container.set_chat_turn_service(
            ChatTurnService(
                pipeline=chat_pipeline,
                memory_service=container.get_memory(),
                session_manager=container.session_manager,
                soul_service=container.soul,
            )
        )
        
        # 4. Skills (Framework)
        from services.managers.skills import SkillManager
        container.skill_manager = SkillManager()

        
        # 4. Ticker
        from services.utilities.ticker import TimeTicker
        container.ticker = TimeTicker()
        container.ticker.start()
        if container.event_bus:
            container.ticker.set_event_bus(container.event_bus)
            
        logger.info("✅ Core Services (LLM, Soul, Session, Ticker) Initialized")

class PluginServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Plugin Services (Vision/TTS/STT)"

    async def bootstrap(self, container):
        try:
            from services.plugin_service import PluginService
            ps = PluginService(container)
            container.set_plugin_service(ps)
            logger.info("✅ Plugin Registry Service Initialized")
        except Exception as e: logger.warning(f"PluginService Init Failed: {e}")

        logger.info("✅ Worker-backed media services delegated to STT/TTS workers")

class MiddlewareBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Middleware (Context/Tools)"
    
    async def bootstrap(self, container):
        # Context Providers
        from services.chat.providers import RAGContextProvider
        container.register_context_provider(RAGContextProvider(container))
        # SoulContextProvider removed to avoid duplicate system prompt (handled in pipeline.py)
        
        # Tool Providers
        from services.chat.tools.search import WebSearchTool
        container.register_tool_provider(WebSearchTool(container))
        
        logger.info("✅ Middleware Registered")

class SystemPluginsBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "System Plugins"
    
    async def bootstrap(self, container):
        from services.system_plugin_manager import SystemPluginManager
        
        rm = getattr(container, 'router_manager', None)
        spm = SystemPluginManager(container=container, router_manager=rm)
        
        await spm.start() # Async Load & Init
        container.system_plugin_manager = spm
        logger.info("✅ System Plugin Manager Initialized")
