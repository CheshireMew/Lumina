import logging
import asyncio
from datetime import datetime
from datetime import timedelta
from typing import Any

from core.interfaces.plugin import BaseSystemPlugin

logger = logging.getLogger("PomodoroManager")

class VirtualTicker:
    def __init__(self, id, name, manager):
        self.id = id
        self.name = name
        self.manager = manager
    
    @property
    def enabled(self):
        return self.manager.enabled

    @enabled.setter
    def enabled(self, value):
        self.manager.enabled = value
            
    @property
    def config(self):
        return {
             "enabled": self.enabled,
             "focus_minutes": self.manager.get_config("focus_minutes", 25),
             "break_minutes": self.manager.get_config("break_minutes", 5)
        }

    @property
    def config_schema(self):
        return {"type": "pomodoro", "key": self.id, "label": "Pomodoro Settings"}


class PomodoroManager(BaseSystemPlugin):
    """
    Pomodoro System Plugin.
    Role: Time Management Service.
    """
    
    @property
    def id(self) -> str:
        return "system.pomodoro"

    @property
    def name(self) -> str:
        return "Pomodoro Timer"

    @property
    def description(self) -> str:
        return "Manages focus and break intervals."

    def initialize(self, context: Any):
        self.context = context
        self.soul = context.soul
        self.ticker = context.ticker
        
        # Subscribe to Seconds (System Standard)
        if context.bus:
            context.bus.subscribe("system.tick", self._on_tick_event)
        elif self.ticker:
            self.ticker.subscribe_seconds(self.on_tick)
            
        # State
        self.state = "IDLE"
        self.end_time = None
        
        # Register Virtual Ticker for Frontend UI
        # We need a way to register this into Heartbeat's list? 
        # OR better: The "Tickers" UI should verify all plugins.
        # But for now, Heartbeat was the aggregator. 
        # If we split it, we might break the "Tickers" list in the frontend if it hardcodes "system.pomodoro" via Heartbeat.
        # However, BaseSystemPlugin doesn't usually expose tickers.
        # We'll assume the frontend iterates all plugins or we might need a "TickerRegistry".
        # For now, let's just make sure it runs. 
        
        logger.info("🍅 Pomodoro Manager Initialized")

    @property
    def enabled(self) -> bool:
         # Use soul config key "system.pomodoro:enabled"
         return self.soul.config.get("ticker.system.pomodoro.enabled", False)

    @enabled.setter
    def enabled(self, value: bool):
         self.soul.config["ticker.system.pomodoro.enabled"] = value

    def get_config(self, key, default):
        return self.soul.config.get(f"ticker.system.pomodoro.{key}", default)

    def _on_tick_event(self, event):
        now = datetime.now()
        if isinstance(event, datetime): now = event
        elif isinstance(event, dict) and "timestamp" in event:
            ts = event["timestamp"]
            if isinstance(ts, str): now = datetime.fromisoformat(ts)
        
        asyncio.create_task(self.on_tick(now))

    async def on_tick(self, now: datetime):
        if not self.enabled:
            return

        conf_focus = self.get_config("focus_minutes", 25)
        conf_break = self.get_config("break_minutes", 5)
        
        if self.state == "IDLE":
            # Auto-start if enabled
            self.state = "FOCUS"
            self.end_time = now + timedelta(minutes=conf_focus)
            self.soul.set_pending_interaction(f"Pomodoro Started ({conf_focus}m). Focus time!", reason="pomodoro")
            logger.info(f"[Pomodoro] Started Focus: {conf_focus}m")
            
        elif self.state == "FOCUS":
            if self.end_time and now >= self.end_time:
                self.state = "BREAK"
                self.end_time = now + timedelta(minutes=conf_break)
                self.soul.set_pending_interaction(f"Pomodoro Focus Complete! Take {conf_break}m break.", reason="pomodoro")
                logger.info("[Pomodoro] Focus -> Break")
                
        elif self.state == "BREAK":
            if self.end_time and now >= self.end_time:
                self.state = "IDLE"
                self.end_time = None
                self.soul.set_pending_interaction("Pomodoro Break over. Ready for next session?", reason="pomodoro")
                logger.info("[Pomodoro] Break -> Idle")
