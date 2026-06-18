
import logging
from .interface import Bootstrapper
from core.runtime import resolve_runtime_port, runtime_target_for_capability

logger = logging.getLogger("Bootstrap.Services")


def _register_worker_service(pm, config, runtime_registry, runtime_id: str, capability: str):
    snapshot = runtime_registry.resolve(runtime_id)
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
        from services.process_manager import ProcessManager
        from services.capability_registry import CapabilityRegistry
        from services.character_service import CharacterService
        # from app_config import config # Global import removed
        runtime_registry = container.get_worker_runtime_registry()
        pm = ProcessManager(runtime_registry)
        
        # [Architecture 5.0] Register Core Services
        config = container.get_config()
        _register_worker_service(pm, config, runtime_registry, "stt-runtime", "stt")
        _register_worker_service(pm, config, runtime_registry, "tts-runtime", "tts")
        _register_worker_service(pm, config, runtime_registry, "vision-runtime", "vision")
        
        container.set_process_manager(pm)
        container.set_worker_runtime_registry(runtime_registry)
        container.set_capability_registry(CapabilityRegistry())
        # 1. LLM
        from llm.manager import LLMManager
        container.set_llm_manager(LLMManager(config))
        
        # 2. Soul (Service)
        from services.orchestrators.soul import SoulService
        from services.repositories.file_soul_repository import FileSoulRepository

        character_id = str(config.memory.character_id or "").strip()
        if not character_id:
            raise ValueError("memory.character_id must be configured")

        container.set_soul(SoulService(
            repo=FileSoulRepository(character_id=character_id),
        ))

        container.set_character_service(CharacterService(
            soul_service=container.get_soul(),
        ))
        
        # 3. Session
        from services.orchestrators.session import SessionManager
        container.set_session_manager(SessionManager(config=container.get_config()))

        from services.companion.context import CompanionContextResolver
        from services.companion.interaction import CompanionInteractionRecorder

        container.set_companion_context_resolver(
            CompanionContextResolver(container.get_soul())
        )
        container.set_companion_interaction_recorder(
            CompanionInteractionRecorder(
                memory_service=container.get_memory(),
                session_manager=container.get_session_manager(),
                soul_service=container.get_soul(),
            )
        )

        from services.chat.pipeline import ChatPipeline
        from services.chat.service import ChatTurnService
        from services.companion.runtime import CompanionRuntime

        chat_pipeline = ChatPipeline(container)
        container.set_chat_pipeline(chat_pipeline)
        container.set_chat_turn_service(
            ChatTurnService(
                pipeline=chat_pipeline,
                session_manager=container.get_session_manager(),
                context_resolver=container.get_companion_context_resolver(),
                interaction_recorder=container.get_companion_interaction_recorder(),
            )
        )
        container.set_companion_runtime(
            CompanionRuntime(chat_turn_service=container.get_chat_turn_service())
        )
        
        # 4. Skills (Framework)
        from services.managers.skills import SkillManager
        container.set_skill_manager(SkillManager())

        
        # 4. Ticker
        from services.utilities.ticker import TimeTicker
        ticker = TimeTicker()
        container.set_ticker(ticker)
        ticker.start()
        ticker.set_event_bus(container.get_event_bus())
            
        logger.info("✅ Core Services (LLM, Soul, Session, Ticker) Initialized")

class ProviderConfigBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Provider Config Service"

    async def bootstrap(self, container):
        from services.provider_config_service import ProviderConfigService

        service = ProviderConfigService(container)
        container.set_provider_config_service(service)
        logger.info("✅ Provider Config Service Initialized")

        logger.info("✅ Worker-backed media services delegated to STT/TTS workers")

class MiddlewareBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Middleware (Context/Tools)"
    
    async def bootstrap(self, container):
        # Context Providers
        from services.chat.providers import RAGContextProvider
        container.register_context_provider(RAGContextProvider(container))
        
        # Tool Providers
        from services.chat.tools.search import WebSearchTool
        container.register_tool_provider(WebSearchTool(container))
        
        logger.info("✅ Middleware Registered")

class CapabilityModulesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Capability Modules"
    
    async def bootstrap(self, container):
        from services.capability_module_manager import CapabilityModuleManager

        manager = CapabilityModuleManager(container=container)
        
        await manager.start()
        container.set_capability_module_manager(manager)
        logger.info("✅ Capability Module Manager Initialized")
