import logging
import random
from datetime import datetime
import asyncio
from typing import Any

from core.interfaces.plugin import BaseSystemPlugin
# Removed Top-level imports to prevent circular dependency
# from services.container import services 
# from llm.manager import llm_manager
# from prompt_manager import prompt_manager
# from services.session_manager import session_manager

logger = logging.getLogger("HeartbeatManager")


# Shim for Legacy Ticker Support
class VirtualTicker:
    def __init__(self, id, name, manager, config_key_prefix=None, interval=1.0):
        self.id = id
        self.name = name
        self.manager = manager
        self.interval = interval
        self.config_prefix = config_key_prefix or id
        # self.config provided by property proxying manager.soul.config?
        # A simple config dict for list_plugins to read
    
    @property
    def enabled(self):
        # Read from Soul Config
        # e.g. "proactive_chat_enabled" or "system.pomodoro:enabled"
        if self.id == "system.proactive":
            return self.manager.soul.config.get("proactive_chat_enabled", True)
        elif self.id == "system.pomodoro":
            # Nested keys not fully supported by soul.config.get in some versions?
            # Assuming flat keys or safe get.
            # Usually stored as "system.pomodoro:enabled" in config kv?
            # For now, store in memory or reuse soul config
            # Let's use a dedicated method in manager to get/set config.
            return self.manager.get_ticker_config(self.id, "enabled", False)
        return False

    @enabled.setter
    def enabled(self, value):
        if self.id == "system.proactive":
            self.manager.soul.config["proactive_chat_enabled"] = value
        else:
            self.manager.set_ticker_config(self.id, "enabled", value)
            
    @property
    def config(self):
        # Expose config values for UI
        conf = {}
        if self.id == "system.proactive":
             conf["timeout_seconds"] = self.manager.soul.config.get("proactive_threshold_minutes", 15.0) * 60
        elif self.id == "system.pomodoro":
             conf["enabled"] = self.enabled
             conf["focus_minutes"] = self.manager.get_ticker_config(self.id, "focus_minutes", 25)
             conf["break_minutes"] = self.manager.get_ticker_config(self.id, "break_minutes", 5)
        return conf


    @property
    def config_schema(self):
        """Returns the UI schema for this ticker."""
        if self.id == "system.proactive":
            return {"type": "number", "key": f"{self.id}:timeout_seconds", "label": "Interval (Sec)"}
        return None

    def start(self):
        self.enabled = True
    
    def stop(self):
        self.enabled = False



class ProactiveManager(BaseSystemPlugin):
    """
    Proactive System Plugin.
    Role: Proactivity & Liveness.
    Subscribes to Global Ticker to check if the AI should initiate conversation.
    """
    
    @property
    def id(self) -> str:
        return "system.proactive"

    @property
    def name(self) -> str:
        return "Proactive System"

    @property
    def description(self) -> str:
        return "Manages idle states and proactive chats."

    @property
    def category(self) -> str:
        return "system"

    @property
    def llm_routes(self) -> list[str]:
        return ["proactive"]

    @property
    def router(self):
        # Lazy import to avoid circular dep
        from .router import router
        return router

    def initialize(self, context: Any):
        # LuminaContext with EventBus
        self.context = context
        
        self.soul = context.soul
        self.ticker = context.ticker
        
        # Subscribe to Tick Events via EventBus (Phase 30 Standard)
        if context.bus:
            context.bus.subscribe("system.tick", self._on_tick_event)
            logger.info("⚡ Proactive subscribed to EventBus 'system.tick'")
        elif self.ticker:
            # Fallback to direct ticker (backward compatibility)
            self.ticker.subscribe_seconds(self.on_tick)
        
        # Register as 'heartbeat_service' via explicit API (Legacy Compat)
        context.register_service("heartbeat_service", self)
        
        self.last_interaction = 0.0 # Shim for callback
        
        # Tickers Registry (for Frontend UI)
        # 🔧 Pomodoro removed (Moved to plugins/system/pomodoro)
        self.tickers = {
            "system.proactive": VirtualTicker("system.proactive", "Active Chat", self)
        }
        
        logger.info("⚡ Proactive Manager Initialized")
    
    def _on_tick_event(self, event):
        """Handler for EventBus tick events."""
        now = datetime.now()
        # Handle various event payload types
        if isinstance(event, datetime):
            now = event
        elif isinstance(event, dict) and "timestamp" in event:
            ts = event["timestamp"]
            if isinstance(ts, datetime):
                now = ts
            elif isinstance(ts, (int, float)):
                now = datetime.fromtimestamp(ts)
                
        # Run on_tick with the extracted time
        asyncio.create_task(self.on_tick(now))

    def get_ticker(self, tid):
        return self.tickers.get(tid)

    def get_ticker_config(self, tid, key, default=None):
        # Store in soul.config with prefix?
        # e.g. "ticker.system.pomodoro.enabled"
        full_key = f"ticker.{tid}.{key}"
        return self.soul.config.get(full_key, default)

    def set_ticker_config(self, tid, key, value):
        full_key = f"ticker.{tid}.{key}"
        self.soul.config[full_key] = value

    async def on_tick(self, now: datetime):
        """
        Called every second by Global Ticker.
        Checks for proactivity conditions.
        """
        try:
            # Check async to avoid blocking ticker
            asyncio.create_task(self._check_and_execute(now))
            

                
        except Exception as e:
            logger.error(f"Heartbeat tick error: {e}")

    async def _check_and_execute(self, now: datetime):
        # 1. Check Master Switch
        if not self.soul.config.get("proactive_chat_enabled", True):
            return

        # 2. Check Gateway Clients (If no one listening, why talk?)
        # Need to expose active_connections count in gateway manager or just try
        # 2. Check Gateway Clients (If no one listening, why talk?)
        from services.container import services
        if not services.gateway or not services.gateway.active_connections:
             # logger.debug("No active clients, skipping proactivity.")
             return

        # 3. Get State & Delta
        state = self.soul.profile.get("state", {})
        last_str = state.get("last_interaction")
        if not last_str: return
        
        try:
            last_dt = datetime.fromisoformat(last_str)
            if last_dt.tzinfo: last_dt = last_dt.replace(tzinfo=None)
        except: return

        delta = (now - last_dt).total_seconds()
        
        # 4. Determine Threshold
        use_custom = self.soul.config.get("heartbeat_enabled", False)
        threshold = 7200 # Default 2 hours
        
        if use_custom:
            mins = self.soul.config.get("proactive_threshold_minutes", 15.0)
            threshold = mins * 60.0
        else:
            rel = self.soul.profile.get("relationship", {})
            level = rel.get("level", 0)
            map_th = { -1: 999999, 0: 7200, 1: 3600, 2: 900, 3: 600 }
            threshold = map_th.get(level, 300) if level < 4 else 300

        # 5. Trigger
        if delta > threshold:
             # Double check lock (using memory/local flag to avoid spamming if task is running)
             # But 'pending_interaction' in soul is still useful as a persistence lock?
             # Let's use it as a mutex.
             if state.get("pending_interaction"): 
                 return

             logger.info(f"鉂わ笍 IDLE TRIGGERED ({delta:.0f}s > {threshold}s). Initiating Push Chat.")
             
             # Set Lock
             self.soul.set_pending_interaction({"reason": "idle_timeout"}, reason="idle_timeout")
             
             # Execute
             await self._perform_push_chat(reason="idle_timeout")

    async def _perform_push_chat(self, reason: str):
        try:
            # A. Prepare Context
            context = {
                "now_str": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "level": self.soul.profile.get("relationship", {}).get("level", 0),
                "current_stage_label": self.soul.profile.get("relationship", {}).get("current_stage_label", "Stranger"),
                "reason": reason,
                "dynamic_instruction": self.soul.profile.get("state", {}).get("dynamic_instruction", ""),
                "char_name": self.soul.config.get("name", "Lumina"),
                "inspiration_text": "" # TODO: Fetch from RAG inspiration endpoint logic?
            }
            
            # Fetch Inspiration (Optional - mimic frontend logic)
            # For MVP, skip or implement MemoryService.get_inspiration() call
            
            # "Proactive chat" implies "AI speaks first".
            # Messages = [ {role: system, content: prompt} ]
            from prompt_manager import prompt_manager
            prompt = prompt_manager.render("proactive/idle.yaml", context)
            messages = [{"role": "system", "content": prompt}]
            
            # B. Get Driver
            # B. Get Driver
            # from llm.manager import llm_manager 
            from services.container import services
            llm_manager = services.get_llm_manager()
            
            driver = await llm_manager.get_driver("proactive")
            model = llm_manager.get_model_name("proactive")
            params = llm_manager.get_parameters("proactive") # Basic
            
            # C. Stream & Push
            logger.info("鈿?Pushing Proactive Stream to Gateway...")
            
            # 1. Start New Session (Interrupt any existing user flow?)
            # Usually proactive waits for idle, so it's safe.
            # But technically it STARTS a new session flow.
            from services.container import services
            session_id = await services.gateway.start_new_session(source="heartbeat")
            
            from core.protocol import EventPacket, EventType

            # Notify Start (Frontend needs to switch mode or just append?)
            await services.gateway.emit(EventPacket(
                session_id=session_id,
                type=EventType.BRAIN_THINKING, # Frontend maps this to "Start"
                source="heartbeat",
                payload={"mode": "proactive"}
            ))
            
            full_content = ""
            async for token in driver.chat_completion(messages, model=model, stream=True, **params):
                if token:
                    full_content += token
                    await services.gateway.emit(EventPacket(
                        session_id=session_id,
                        type=EventType.BRAIN_RESPONSE, # Frontend maps this to "Token"
                        source="heartbeat",
                        payload={"content": token}
                    ))
            
            # Send End
            await services.gateway.emit(EventPacket(
                session_id=session_id,
                # type=EventType.BRAIN_RESPONSE, # Using custom end type below
                # Protocol says INPUT_AUDIO_END but not OUTPUT_END explicitly.
                # Usually stream just stops or sends special packet.
                # Let's send a control packet or rely on frontend timeout?
                # No, better explicit. Re-use BRAIN_RESPONSE with finish_reason?
                # Or just use "chat_end" type for now if we add it to whitelist or map it.
                # Let's add BRAIN_RESPONSE_END?
                # For now, stick to BRAIN_RESPONSE with a flag or just let frontend detect.
                # Actually, in new architecture, Silence is mostly implied.
                # But for Frontend stream handler, it needs an "Done" signal to clean up Ref buffers.
                # Let's send a dedicated type "brain_response_end" (custom string valid in Pydantic str field)
                # Let's send a dedicated type "brain_response_end" (custom string valid in Pydantic str field)
                type="brain_response_end", 
                source="heartbeat",
                payload={}
            ))
            
            # D. Update History & Reset Timer
            # Record it as Assistant Message
            # But "User" didn't say anything. 
            # SessionManager: add_turn expects user/ai.
            # We can add just AI message?
            from services.session_manager import session_manager
            session_manager.get_session("default_user", self.soul.character_id).add_message("assistant", full_content)
            
            # Clear Pending Lock & Update Timestamp
            # self.soul.mutate(clear_pending=True) # Logic exists in router `soul/mutate`
            # We call internal method?
            # SoulManager doesn't have clear_pending method explicitly public?
            # It has 'record_interaction'.
            self.soul.update_state("state.last_interaction", datetime.now().isoformat())
            self.soul.update_state("state.pending_interaction", None)
            
            logger.info("鉁?Proactive Chat Completed & State Reset.")

        except Exception as e:
            logger.error(f"Proactive Chat Failed: {e}")
            # Reset lock to retry later? Or backoff?
            # If we don't clear lock, it blocks forever.
            # If we don't clear lock, it blocks forever.
            self.soul.update_state("state.pending_interaction", None)


