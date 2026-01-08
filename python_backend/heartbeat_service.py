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
    
    def __init__(self, soul_manager: SoulManager, hippocampus=None, graph_curator=None, main_loop=None):
        self.soul = soul_manager
        self.hippocampus = hippocampus  # Hippocampus 引用（用于空闲触发消化）
        self.graph_curator = graph_curator # Graph Curator 引用 (用于周期性维护)
        self.main_loop = main_loop      # 主事件循环（用于跨线程调用异步方法）
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
        检查是否需要触发 Hippocampus 消化。
        条件: 空闲 5 分钟以上，且上次消化已超过 5 分钟。
        """
        import asyncio
        
        # 1. 检查是否有 Hippocampus 引用和主循环
        if not self.hippocampus or not self.main_loop:
            return
        
        # 2. 检查是否正在处理中
        if self._digest_in_progress:
            return
        
        # 3. 检查空闲时间是否达到阈值 (5 分钟) -> 进入 "Dreaming State"
        is_dreaming_state = seconds_idle >= self._digest_idle_threshold
        
        if not is_dreaming_state:
            return
            
        # 4. 检查距离上次消化是否超过间隔
        # 如果处于 Dreaming State，我们使用较短的间隔 (10s) 连续处理
        now = datetime.now()
        threshold = self._digest_interval_active
        
        if self._last_digest_time:
            elapsed = (now - self._last_digest_time).total_seconds()
            if elapsed < threshold:
                return
        
        # 5. 触发消化
        # print(f"[Heartbeat] 🧠 DREAMING: Idle {seconds_idle:.0f}s, processing next memory batch...")
        self._digest_in_progress = True
        self._last_digest_time = now
        
        try:
            # 使用主循环执行异步任务，确保 SurrealDB 连接在正确的 loop 中使用
            future = asyncio.run_coroutine_threadsafe(
                self.hippocampus.process_memories(batch_size=1), 
                self.main_loop
            )
            
            # 等待结果（可选，如果在线程中不希望阻塞太久，可以不等待，但为了逻辑安全这里等待）
            try:
                future.result(timeout=60) # 设置超时防止死锁
                print("[Heartbeat] ✅ Hippocampus digest complete")
            except asyncio.TimeoutError:
                print("[Heartbeat] ⚠️ Hippocampus digest timed out")
            except Exception as e:
                print(f"[Heartbeat] ❌ Hippocampus digest failed: {e}")
                
        except Exception as e:
            print(f"[Heartbeat] ❌ Threadsafe call failed: {e}")
        finally:
            self._digest_in_progress = False

    def _check_maintenance_schedule(self):
        """检查并触发每日图谱维护"""
        if not self.graph_curator or not self.main_loop: return

        now = datetime.now()
        elapsed = (now - self._last_maintenance_time).total_seconds()
        
        if elapsed > self._maintenance_interval_seconds:
            print(f"[Heartbeat] 🌿 Scheduled Maintenance: Triggering Graph Curator...")
            self._last_maintenance_time = now
            
            # 异步调用 run_maintenance
            import asyncio
            future = asyncio.run_coroutine_threadsafe(
                self.graph_curator.run_maintenance(),
                self.main_loop
            )
            # Log result via callback or fire-and-forget logic


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
            # Check if already pending to avoid spam
            if "pending_interaction" not in state:
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
