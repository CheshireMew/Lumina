
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
        from app_config import BASE_DIR, DATA_ROOT
        from services.process_manager import ProcessManager
        from services.character_service import CharacterService
        # from app_config import config # Global import removed
        runtime_registry = container.get_worker_runtime_registry()
        pm = ProcessManager(runtime_registry)
        
        # [Architecture 5.0] Register Core Services
        config = container.get_config()
        for capability in runtime_registry.list_worker_capabilities():
            definition = runtime_registry.runtime_for_capability(capability)
            if definition:
                _register_worker_service(
                    pm,
                    config,
                    runtime_registry,
                    definition.id,
                    capability,
                )
        
        container.set_process_manager(pm)
        container.set_worker_runtime_registry(runtime_registry)
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
            repo=FileSoulRepository(
                character_id=character_id,
                characters_root=DATA_ROOT / "characters",
                seed_characters_root=BASE_DIR / "characters",
            ),
        ))

        container.set_character_service(CharacterService(
            soul_service=container.get_soul(),
            characters_root=DATA_ROOT / "characters",
            seed_characters_root=BASE_DIR / "characters",
        ))
        
        # 3. Session
        from services.orchestrators.session import SessionManager
        from services.repositories.file_session_repository import FileSessionRepository
        container.set_session_manager(SessionManager(
            repo=FileSessionRepository(DATA_ROOT / "sessions"),
            config=container.get_config(),
        ))

        from services.companion.context import CompanionContextResolver
        from services.companion.context_pack import CompanionContextPackBuilder
        from services.companion.interaction import CompanionInteractionRecorder
        from services.companion.post_turn_journal import PostTurnJournal
        from memory.consolidation import MemoryConsolidationService

        container.set_memory_consolidation_service(
            MemoryConsolidationService(
                memory_service=container.get_memory(),
                llm_manager=container.get_llm_manager(),
            )
        )
        container.set_post_turn_journal(
            PostTurnJournal(DATA_ROOT / "operations" / "post_turn")
        )

        container.set_companion_context_resolver(
            CompanionContextResolver(container.get_soul())
        )
        container.set_companion_interaction_recorder(
            CompanionInteractionRecorder(
                memory_service=container.get_memory(),
                session_manager=container.get_session_manager(),
                soul_service=container.get_soul(),
                journal=container.get_post_turn_journal(),
                consolidation_service=container.get_memory_consolidation_service(),
            )
        )
        container.set_companion_context_pack_builder(
            CompanionContextPackBuilder(
                session_manager=container.get_session_manager(),
                memory_service=container.get_memory(),
                soul_service=container.get_soul(),
                config=container.get_config(),
            )
        )

        from services.chat.pipeline import ChatPipeline
        from services.chat.service import ChatTurnService
        from services.companion.runtime import CompanionRuntime

        chat_pipeline = ChatPipeline(
            container.get_llm_manager(),
            container.get_all_tools,
            container.get_tool_provider,
        )
        container.set_chat_pipeline(chat_pipeline)
        container.set_chat_turn_service(
            ChatTurnService(
                pipeline=chat_pipeline,
                session_manager=container.get_session_manager(),
                context_resolver=container.get_companion_context_resolver(),
                context_pack_builder=container.get_companion_context_pack_builder(),
                interaction_recorder=container.get_companion_interaction_recorder(),
            )
        )
        container.set_companion_runtime(
            CompanionRuntime(
                chat_turn_service=container.get_chat_turn_service(),
                context_resolver=container.get_companion_context_resolver(),
                session_manager=container.get_session_manager(),
            )
        )

        await container.get_companion_interaction_recorder().recover_pending()
        await container.get_memory_consolidation_service().schedule(
            container.get_companion_context_resolver().resolve()
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

        from services.config_service import ConfigService

        config_service = ConfigService(
            container.get_config(),
            container.get_llm_manager(),
        )
        service = ProviderConfigService(
            config=container.get_config(),
            process_manager=container.get_process_manager(),
            worker_control_hub=container.get_worker_control_hub(),
            config_service=config_service,
        )
        container.set_provider_config_service(service)
        logger.info("✅ Provider Config Service Initialized")

        logger.info("✅ Worker-backed media services delegated to STT/TTS workers")

class MiddlewareBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Middleware (Context/Tools)"
    
    async def bootstrap(self, container):
        from services.chat.emotion_broker import EmotionBroker
        # Tool Providers
        from services.chat.tools.search import WebSearchTool
        from services.chat.search_providers import BraveSearchProvider, DuckDuckGoSearchProvider
        container.register_search_provider(BraveSearchProvider(container.get_config()))
        container.register_search_provider(DuckDuckGoSearchProvider(container.get_config()))
        container.register_tool_provider(
            WebSearchTool(container.get_config(), container.get_search_provider)
        )

        emotion_broker = EmotionBroker(container.get_event_bus(), container.get_config())
        emotion_broker.start()
        container.set_emotion_broker(emotion_broker)
        
        logger.info("✅ Middleware Registered")
