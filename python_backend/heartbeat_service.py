import time
import random
import threading
from datetime import datetime, timedelta
from soul_manager import SoulManager
# from tts_engine import TTSEngine # Future integration

class HeartbeatService:
    """
    The 'Cognitive Heartbeat' of Lumina.
    Runs in the background to provide:
    1. Proactivity (Initiating conversation based on Intimacy).
    2. State Decay (Energy drops over time).
    3. Time Awareness.
    """
    
    def __init__(self, soul_manager: SoulManager):
        self.soul = soul_manager
        self.running = False
        self.thread = None
        # 记录上次行动的时间，避免日志刷屏
        self.last_log_time = datetime.now()
        
    def start(self):
        if self.running: return
        self.running = True
        self.thread = threading.Thread(target=self._bdi_loop, daemon=True)
        self.thread.start()
        print("[Heartbeat] ❤️ Service Started. (Interval: 10s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("[Heartbeat] Service Stopped.")

    def _bdi_loop(self):
        """
        Belief-Desire-Intention (BDI) Loop.
        Simplification:
        - CHECK every 10 seconds.
        - ACTION: Decay energy slowly.
        - ACTION: Check idle time for proactivity.
        """
        while self.running:
            try:
                self._pulse()
            except Exception as e:
                print(f"[Heartbeat] Error in pulse: {e}")
            
            # Sleep for a bit (simulate thought interval)
            time.sleep(10) 

    def _pulse(self):
        """One cognitive cycle."""
        profile = self.soul.profile
        state = profile.get("state", {})
        rel = profile.get("relationship", {})
        
        # 1. Decay Energy: REMOVED per user request (Event-based only)
        # self.soul.update_energy(-0.03) 
        
        # 2. Check for Proactivity
        # ⚡ Logic Update:
        # custom_mode = True  -> Use proactive_threshold_minutes
        # custom_mode = False -> Use Intimacy Level Logic
        
        use_custom_threshold = self.soul.config.get("heartbeat_enabled", False) # Default to Auto if missing? Or User preference.
        
        last_interaction_str = state.get("last_interaction")
        if not last_interaction_str:
            return
            
        # Parse time
        try:
            last_dt = datetime.fromisoformat(last_interaction_str)
            if last_dt.tzinfo is not None:
                last_dt = last_dt.replace(tzinfo=None)
        except ValueError:
            return

        delta = datetime.now() - last_dt
        seconds_idle = delta.total_seconds()
        
        level = rel.get("level", 0) # ⚡ Fix: Define level here so it's available for logging later
        threshold = 7200 # Default 2 hours

        if use_custom_threshold:
            # ⚡ Custom Mode
            config_threshold_mins = self.soul.config.get("proactive_threshold_minutes", 15.0)
            threshold = config_threshold_mins * 60.0
            # print(f"[Heartbeat] Mode: Custom ({config_threshold_mins}m)")
        else:
            # ⚡ Auto (Intimacy) Mode
            # level defined above
            if level < 0: threshold = 999999 
            elif level == 0: threshold = 7200 # 2 hours
            elif level == 1: threshold = 3600 # 1 hour
            elif level == 2: threshold = 900  # 15 mins
            elif level == 3: threshold = 600  # 10 mins
            elif level >= 4: threshold = 300  # 5 mins
            # print(f"[Heartbeat] Mode: Auto (Level {level} -> {threshold}s)")

        # Log periodically (every minute) if significantly idle
        if seconds_idle > 60 and (datetime.now() - self.last_log_time).total_seconds() > 60:
             # self.last_log_time = datetime.now()
             pass
        
        if seconds_idle > threshold:
            # Trigger Proactivity
            print(f"[Heartbeat] ❤️ IDLE DETECTED: {seconds_idle:.1f}s > {threshold}s. Initiating...")
            # print(f"[Heartbeat] Idle for {seconds_idle:.0f}s. Threshold: {threshold}s. Energy: {state.get('energy_level', 0):.1f}")
            self.last_log_time = datetime.now()
        
        if seconds_idle > threshold:
            # We want to talk!
            # Check if already pending to avoid spam
            if "pending_interaction" not in state:
                print(f"[Heartbeat] ❤️ DESIRE: I miss the user... (Level: {level}) -> Setting Pending Flag")
                self.soul.set_pending_interaction(True, reason="idle_timeout") 

if __name__ == "__main__":
    hb = HeartbeatService()
    hb.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        hb.stop()
