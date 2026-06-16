
import logging
from .interface import Bootstrapper
from core.runtime import resolve_runtime_port, runtime_target_for_capability

logger = logging.getLogger("Bootstrap.Services")


def _register_worker_service(pm, config, package_registry, package_id: str, capability: str):
    snapshot = package_registry.resolve(package_id)
    if not snapshot or snapshot.status != "ready" or not snapshot.entry_arguments:
        return

    runtime_target = runtime_target_for_capability(capability)
    port = resolve_runtime_port(config, runtime_target)
    if not port:
        raise ValueError(f"No port configured for capability '{capability}'")

    args = list(snapshot.entry_arguments)
    script_name = str(snapshot.entry_executable) if snapshot.entry_executable else "backend_launcher.py"
    pm.register_service_def(
        runtime_target,
        port,
        script_name,
        args,
        cwd=str(snapshot.root_dir) if snapshot.root_dir else None,
    )

class CoreServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Core Services"

    async def bootstrap(self, container):
        from core.capability_packages import CapabilityPackageRegistry
        from services.process_manager import ProcessManager
        from services.capability_registry import CapabilityRegistry
        from services.character_service import CharacterService
        # from app_config import config # Global import removed
        pm = ProcessManager()
        package_registry = CapabilityPackageRegistry()
        pm.set_capability_package_registry(package_registry)
        
        # [Architecture 5.0] Register Core Services
        config = container.get_config()
        _register_worker_service(pm, config, package_registry, "stt-runtime", "stt")
        _register_worker_service(pm, config, package_registry, "tts-runtime", "tts")
        _register_worker_service(pm, config, package_registry, "vision-runtime", "vision")
        
        container.set_process_manager(pm)
        container.set_capability_package_registry(package_registry)
        container.set_capability_registry(CapabilityRegistry())
        container.set_character_service(CharacterService(
            package_registry=package_registry,
            system_config=container.get_config(),
        ))

        # 1. LLM
        from llm.manager import LLMManager
        container.set_llm_manager(LLMManager())
        
        # 2. Soul (Service)
        from services.orchestrators.soul import SoulService
        container.set_soul(SoulService(
            system_config=container.get_config(),
            memory_service=container.get_memory(),
        ))
        
        # 3. Session
        from services.orchestrators.session import SessionManager
        container.set_session_manager(SessionManager(config=container.get_config()))

        from services.chat.pipeline import ChatPipeline
        from services.chat.service import ChatTurnService

        chat_pipeline = ChatPipeline(container)
        container.set_chat_pipeline(chat_pipeline)
        container.set_chat_turn_service(
            ChatTurnService(
                pipeline=chat_pipeline,
                memory_service=container.get_memory(),
                session_manager=container.get_session_manager(),
                soul_service=container.get_soul(),
            )
        )
        
        # 4. Skills (Framework)
        from services.managers.skills import SkillManager
        container.set_skill_manager(SkillManager())

        
        # 4. Ticker
        from services.utilities.ticker import TimeTicker
        ticker = TimeTicker()
        container.set_ticker(ticker)
        ticker.start()
        if container.has_service("event_bus"):
            ticker.set_event_bus(container.get_event_bus())
            
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

        spm = SystemPluginManager(container=container)
        
        await spm.start() # Async Load & Init
        container.set_system_plugin_manager(spm)
        logger.info("✅ System Plugin Manager Initialized")
