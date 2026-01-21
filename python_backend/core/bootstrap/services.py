
import logging
from .interface import Bootstrapper

logger = logging.getLogger("Bootstrap.Services")

class CoreServicesBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Core Services"

    async def bootstrap(self, container):
        # 0. Process Manager [Arch 4.0]
        from services.process_manager import ProcessManager
        from app_config import config
        pm = ProcessManager()
        
        # [Architecture 5.0] Register Core Services
        pm.register_service_def("stt_server", config.network.stt_port, "backend_launcher.py", ["stt"])
        pm.register_service_def("tts_server", config.network.tts_port, "backend_launcher.py", ["tts"])
        
        container.set_process_manager(pm)

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
            from services.vision_service import vision_service
            container.set_vision(vision_service)
        except Exception as e: logger.warning(f"Vision Init Failed: {e}")
        
        # TTS
        try:
            from services.tts_manager import TTSPluginManager
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
            # [Fix] Monolith Mode: Auto-activate drivers immediately
            await sm.register_drivers(auto_activate=True)
            
            container.stt = sm

            # [Fix] Initialize AudioManager (Main Process)
            # This ensures stt_routes.py has access to audio hardware and callbacks
            from services.audio_manager import AudioManager
            import services.stt.globals as stt_globals
            import threading

            def on_speech_start():
                 stt_globals.message_queue.put({"type": "vad_status", "status": "listening"})
            
            def on_speech_end(audio_data):
                 def _transcribe():
                     try:
                         # Transcribe synchronously in thread
                         res = sm.transcribe(audio_data)
                         if res and res.get("text"):
                             logger.info(f"🎤 STT: {res['text']}")
                             stt_globals.message_queue.put({"type": "transcription", "text": res['text']})
                     except Exception as e:
                         logger.error(f"Transcribe Error: {e}")
                 
                 # Offload to thread to prevent blocking Audio Callback
                 threading.Thread(target=_transcribe).start()

            def on_vad_change(status):
                 stt_globals.message_queue.put({"type": "vad_status", "status": status})

            logger.info("🎤 Initializing AudioManager (Main Process)...")
            am = AudioManager(
                on_speech_start=on_speech_start,
                on_speech_end=on_speech_end,
                on_vad_status_change=on_vad_change
            )
            stt_globals.audio_manager = am
            
        except Exception as e: logger.warning(f"STT Init Failed: {e}", exc_info=True)
        
        # [Architecture 5.0] High-Level Service Registry
        try:
            from services.plugin_service import PluginService
            ps = PluginService(container)
            container.set_plugin_service(ps)
            logger.info("✅ Plugin Registry Service Initialized")
        except Exception as e: logger.warning(f"PluginService Init Failed: {e}")

        logger.info("✅ Media Services Initialized")

class MiddlewareBootstrapper(Bootstrapper):
    @property
    def name(self) -> str: return "Middleware (Context/Tools)"
    
    async def bootstrap(self, container):
        # Context Providers
        from services.chat.providers import RAGContextProvider
        container.register_context_provider(RAGContextProvider())
        # SoulContextProvider removed to avoid duplicate system prompt (handled in pipeline.py)
        
        # Tool Providers
        from services.chat.tools.search import WebSearchTool
        container.register_tool_provider(WebSearchTool())
        
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
