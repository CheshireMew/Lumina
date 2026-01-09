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
    4. Hippocampus Digest Trigger (After 5 min idle).
    """
    
    def __init__(self, soul_manager: SoulManager, dreaming=None, main_loop=None):
        self.soul = soul_manager
        self.dreaming = dreaming  # Dreaming Service Ref
        self.main_loop = main_loop      # Event Loop
        self.running = False
        self.thread = None
        # 记录上次行动的时间，避免日志刷屏
        self.last_log_time = datetime.now()
        # Hippocampus 消化状态
        self._last_digest_time: datetime = None
        self._digest_idle_threshold = 300  # Enter Dreaming Mode after 5 min idle
        self._digest_interval_active = 10   # Process every 10s while Dreaming
        self._digest_in_progress = False
        # Graph Maintenance 状态
        self._last_maintenance_time = datetime.now()
        self._maintenance_interval_seconds = 86400 # 24 Hours
        
    def start(self):
        if self.running: return
        self.running = True
        
        # ⚡ 修复：启动时重置 last_interaction 为当前时间，避免立即触发空闲检测
        self.soul.update_last_interaction()
        print("[Heartbeat] ⏰ Reset last_interaction to now")
        
        self.thread = threading.Thread(target=self._bdi_loop, daemon=True)
        self.thread.start()
        print("[Heartbeat] ❤️ Service Started. (Interval: 10s)")

    def stop(self):
        self.running = False
        if self.thread:
            self.thread.join()
        print("[Heartbeat] Service Stopped.")

    def _check_and_trigger_digest(self, seconds_idle: float):
        """
        Check if we should trigger Dreaming.
        Condition: Idle > 5 mins.
        """
        import asyncio
        
        # DEBUG: Check entry
        # print(f"[Heartbeat] Checking digest trigger... Dreaming={bool(self.dreaming)}, Loop={bool(self.main_loop)}, InProgress={self._digest_in_progress}")
        
        # 1. Check Dependencies
        if not self.dreaming or not self.main_loop:
            return
        
        # 2. Check Lock
        if self._digest_in_progress: return
        
        # 3. Rate Limiting (Poll Interval)
        # We now poll periodically regardless of idle state, because Dreaming service checks counts efficiently.
        now = datetime.now()
        threshold = self._digest_interval_active
        if self._last_digest_time:
            elapsed = (now - self._last_digest_time).total_seconds()
            if elapsed < threshold: return
        
        # 5. Trigger Dreaming
        # print(f"[Heartbeat] 💤 Dreaming Cycle (Idle {seconds_idle:.0f}s)...")
        self._digest_in_progress = True
        self._last_digest_time = now
        
        def on_complete(future):
            """异步任务完成后释放锁"""
            self._digest_in_progress = False
            try:
                future.result()  # 捕获异常
            except Exception as e:
                print(f"[Heartbeat] ❌ Dreaming failed: {e}")
        
        try:
            future = asyncio.run_coroutine_threadsafe(
                self.dreaming.process_memories(),
                self.main_loop
            )
            future.add_done_callback(on_complete)
        except Exception as e:
            print(f"[Heartbeat] ❌ Threadsafe call failed: {e}")
            self._digest_in_progress = False  # 只有在调用失败时立即释放

    def _check_maintenance_schedule(self):
        """Deprecated: Graph Maintenance"""
        pass


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
                self._check_maintenance_schedule() # ADDED CHECK
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
            # ⚡ 修复：检查值是否为真（not None/False），而非检查 key 是否存在
            if not state.get("pending_interaction"):
                print(f"[Heartbeat] ❤️ DESIRE: I miss the user... (Level: {level}) -> Setting Pending Flag")
                self.soul.set_pending_interaction(True, reason="idle_timeout") 
        
        # ==================== Hippocampus Digest (5 Min Idle) ====================
        self._check_and_trigger_digest(seconds_idle) 

if __name__ == "__main__":
    hb = HeartbeatService()
    hb.start()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        hb.stop()
