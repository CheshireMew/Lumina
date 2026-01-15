# from .base import BaseTicker, HeartbeatContext
from plugins.tickers.base import BaseTicker, HeartbeatContext
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("PomodoroTicker")

class PomodoroTicker(BaseTicker):
    def __init__(self):
        super().__init__("system.pomodoro", "Pomodoro Timer", interval=1.0)
        self.config = {
            "enabled": False,
            "focus_minutes": 25,
            "break_minutes": 5,
            "strict_mode": False
        }
        # State: IDLE, FOCUS, BREAK
        self.state = "IDLE" 
        self._end_time: datetime = None
        self._last_minute_announce = -1

    def on_time_up(self, context: HeartbeatContext):
        if self.state == "FOCUS":
            # Focus done -> Break
            self.state = "BREAK" 
            break_min = self.config.get("break_minutes", 5)
            self._end_time = datetime.now() + timedelta(minutes=break_min)
            context.soul.set_pending_interaction(f"Pomodoro Focus Session Complete! Tell user to take a {break_min} minute break.")
            logger.info("Pomodoro: Focus -> Break")
        
        elif self.state == "BREAK":
            # Break done -> Idle
            self.state = "IDLE"
            self._end_time = None
            context.soul.set_pending_interaction("Break is over. Ask user if they want to start another session.")
            logger.info("Pomodoro: Break -> Idle")

    def on_tick(self, now: datetime, context: HeartbeatContext):
        # 1. Check consistency
        if not self.config.get("enabled"):
            if self.state != "IDLE":
                self.state = "IDLE" # Force reset if disabled
                self._end_time = None
            return

        # 2. State Machine
        if self.state == "IDLE":
            # Wait for user to START via API (we need an action endpoint for this)
            # For MVP: If enabled, we auto-start? No, weird.
            # We need a 'start_time' or a command.
            # Let's assume enabling it via config STARTS it for now (MVP).
            # Improvements: Add 'start' command in UI.
            
            # Auto-start for MVP when enabled
            self.state = "FOCUS"
            mins = self.config.get("focus_minutes", 25)
            self._end_time = now + timedelta(minutes=mins)
            context.soul.set_pending_interaction(f"Pomodoro Timer Started ({mins} mins). Encourage user to focus.")
            logger.info(f"Pomodoro Started: {mins}m")
        
        elif self.state in ["FOCUS", "BREAK"]:
            if self._end_time and now >= self._end_time:
                self.on_time_up(context)
            else:
                # Optional: Announce remaining time periodically?
                # Maybe at 5 mins remaining?
                pass
                
    def get_config_schema(self):
        return {
            "enabled": {"type": "boolean", "label": "Enable Pomodoro (Auto-Start)"},
            "focus_minutes": {"type": "number", "label": "Focus Time (m)", "min": 1, "max": 120},
            "break_minutes": {"type": "number", "label": "Break Time (m)", "min": 1, "max": 30},
            "strict_mode": {"type": "boolean", "label": "Strict Mode (Block Chat)"}
        }
