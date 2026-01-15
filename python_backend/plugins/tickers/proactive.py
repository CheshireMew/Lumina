# from .base import BaseTicker, HeartbeatContext
from plugins.tickers.base import BaseTicker, HeartbeatContext
from datetime import datetime, timedelta
import logging

logger = logging.getLogger("ProactiveTicker")

class ProactiveTicker(BaseTicker):
    def __init__(self):
        super().__init__("system.proactive_chat", "Proactive Chat", interval=5.0)
        # Default Config
        self.config = {
            "enabled": False,
            "timeout_seconds": 60, # Silence threshold
            "cooldown_seconds": 300 # Don't trigger too often
        }
        self._last_trigger_time = datetime.fromtimestamp(0)

    def on_tick(self, now: datetime, context: HeartbeatContext):
        # 1. Check if we should trigger based on idle time
        if not self.config.get("enabled"): return

        last_interact = context.soul.last_interaction or now
        timeout = self.config.get("timeout_seconds", 60)
        
        idle_seconds = (now - last_interact).total_seconds()
        
        # Condition 1: User is Silent for > Timeout
        if idle_seconds > timeout:
            # Condition 2: Cooldown check (Don't spam)
            # Use max of (last_trigger, last_interaction) to avoid triggering immediately after a conversation ends 
            # if the conversation duration was short? 
            # Actually, context.soul.last_interaction updates when user OR bot speaks usually?
            # Let's assume last_interaction is updated on ANY exchange.
            
            # Additional Cooldown: Ensure we haven't triggered PROACTIVELY recently
            # independent of whether user replied.
            time_since_last_trigger = (now - self._last_trigger_time).total_seconds()
            cooldown = self.config.get("cooldown_seconds", 300)
            
            if time_since_last_trigger > cooldown:
                # 鈿?TRIGGER!
                logger.info(f"[ProactiveTicker] Idle {idle_seconds:.1f}s > {timeout}s. Triggering chat.")
                
                # Check if there is already a pending interaction?
                # Soul manager should handle this, but let's be safe.
                # Use a specific type of pending interaction so frontend knows?
                # For now, simplistic string.
                
                # We need to construct a "Prompt" for the soul to start talking.
                # Usually we set 'pending_interaction' to a reason string.
                context.soul.set_pending_interaction(f"User has been silent for {int(idle_seconds)} seconds. Initiate a conversation casually.")
                
                self._last_trigger_time = now

    def get_config_schema(self):
        return {
            "enabled": {"type": "boolean", "label": "Enable Proactive Chat"},
            "timeout_seconds": {"type": "number", "label": "Silence Timeout (s)", "min": 10, "max": 3600},
            "cooldown_seconds": {"type": "number", "label": "Cooldown (s)", "min": 60, "max": 3600}
        }
