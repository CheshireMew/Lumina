
import logging
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Services")

class CoreServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Core Services"

    async def bootstrap(self, container):
        # 1. LLM
        from llm.manager import LLMManager
        container.llm_manager = LLMManager()
        
        # 2. Soul (Service)
        from services.soul_service import SoulService
        container.soul = SoulService() # No more character_id hardcoding here!
        
        # 3. Session
        from services.session_manager import SessionManager
        container.session_manager = SessionManager()
        
        # 4. Skills (Framework)
        from services.skill_manager import SkillManager
        container.skill_manager = SkillManager()

        
        # 4. Ticker
        from services.global_ticker import TimeTicker
        container.ticker = TimeTicker()
        container.ticker.start()
        if container.event_bus:
            container.ticker.set_event_bus(container.event_bus)
            
        logger.info("✅ Core Services (LLM, Soul, Session, Ticker) Initialized")

class PluginServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Plugin Services (Vision/TTS/STT)"

    async def bootstrap(self, container):
        # Vision
        try:
            from vision_service import VisionPluginManager
            vm = VisionPluginManager()
            container.set_vision(vm)
        except Exception as e: logger.warning(f"Vision Init Failed: {e}")
        
        # TTS
        try:
            from tts_server import TTSPluginManager
            tm = TTSPluginManager()
            # ⚠️ Lazy Mode: Do not load models in Main Process
            if self.name == "Plugin Services (Vision/TTS/STT)":
                 await tm.register_drivers(auto_activate=False) 
            else:
                 await tm.register_drivers()
            container.set_tts(tm)
        except Exception as e: logger.warning(f"TTS Init Failed: {e}")

        # STT
        try:
            from services.stt_manager import STTPluginManager
            sm = STTPluginManager()
            # ⚠️ Lazy Mode: Do not load models in Main Process
            if self.name == "Plugin Services (Vision/TTS/STT)": # Defensive check if needed, or just standard
                 await sm.register_drivers(auto_activate=False)
            else:
                 await sm.register_drivers() # Should not happen here
            
            container.stt = sm
        except Exception as e: logger.warning(f"STT Init Failed: {e}")
        
        logger.info("✅ Media Services Initialized")

class MiddlewareBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Middleware (Context/Tools)"
    
    async def bootstrap(self, container):
        # Context Providers
        from services.chat.providers import RAGContextProvider, SoulContextProvider
        container.register_context_provider(RAGContextProvider())
        container.register_context_provider(SoulContextProvider())
        
        # Tool Providers
        from services.chat.tools.search import WebSearchTool
        container.register_tool_provider(WebSearchTool())
        
        logger.info("✅ Middleware Registered")

class SystemPluginsBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "System Plugins"
    
    async def bootstrap(self, container):
        from services.system_plugin_manager import SystemPluginManager
        spm = SystemPluginManager(container=container)
        await spm.start() # Async Load & Init
        container.system_plugin_manager = spm
        logger.info("✅ System Plugin Manager Initialized")
