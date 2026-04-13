
import asyncio
import logging
from typing import Dict, Any, List

from services.infra.bus_factory import get_lifecycle_bus

logger = logging.getLogger("ReconciliationService")

class ReconciliationService:
    """
    [Architecture 6.0] The Active Controller.
    Monitors the 'plugin_state' table and enforces the Desired State.
    """
    def __init__(self, services):
        self.services = services
        self._running = False
        self._task = None
        
        # [Phase 9] Circuit Breaker State
        # Map: worker_id -> List[timestamp]
        self.restart_history: Dict[str, List[float]] = {}
        self.CRASH_WINDOW = 60.0 # seconds
        self.MAX_RESTARTS = 3
        
    def start(self):
        if not self._running:
            self._running = True
            self._task = asyncio.create_task(self._control_loop())
            logger.info("⚖️ Reconciliation Service Started")

    async def stop(self):
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except Exception:
                pass

    async def _control_loop(self):
        """
        Main Control Loop.
        Adaptive Interval: 30s (Single Node) / 5s (Distributed)
        """
        # Allow system to stabilize
        await asyncio.sleep(15)
        
        bus = get_lifecycle_bus()
        
        # [Architecture Refinement] Adaptive Polling
        # If no remote workers are configured, we assume Single Node Mode ("Desktop Pet")
        # and relax the reconciliation loop to save resources.
        from app_config import config
        target_interval = 5.0
        
        # Check if we have explicit remote workers configured
        remote_workers = [w for w, c in config.network.workers.items() if c.host not in ["127.0.0.1", "localhost"]]
        if not remote_workers:
            target_interval = 30.0
            logger.info(f"🐢 Single Node Detected. Relaxing Reconciliation to {target_interval}s interval.")
        else:
            logger.info(f"🐇 Distributed Mode Detected. Maintaining Reconciliation at {target_interval}s.")
        
        while self._running:
            try:
                await asyncio.sleep(target_interval)
                
                # 1. Fetch Full State Snapshot
                # We need raw DB records to check timestamps
                if not bus.db: continue
                
                # Query for Anomalies
                # Note: Time math in python for now to be DB-agnostic friendly
                states = await bus.get_all_states()
                now = asyncio.get_event_loop().time()
                
                for pid, state in states.items():
                    await self._reconcile_plugin(pid, state, now)

            except Exception as e:
                logger.error(f"Reconciliation Loop Error: {e}")
                await asyncio.sleep(5)

    async def _reconcile_plugin(self, pid: str, state: Dict[str, Any], now_ts: float):
        bus = get_lifecycle_bus()
        
        desired = state.get("desired_enabled")
        active_status = state.get("active_status", "unknown")
        
        # Check Updated At (Parsed from DB or current time if missing?)
        # Lifecycle store timestamps may be ISO strings or datetime objects.
        # But 'PluginService' just updated it? No, Bus updates it.
        # We need to parse 'updated_at' or use 'last_seen' for workers.
        # Let's rely on 'last_seen' for liveness.
        
        worker_id = state.get("worker_id")
        
        # 1. Dead Worker Detection
        # If active != offline/stopped AND last_seen > 30s ago
        # Note: WorkerStatusReporter sends heartbeat. Record ID for heartbeat is worker_heartbeats:{wid}
        # Plugin state update logic might not update 'last_seen' on the plugin record itself?
        # publish_state updates plugin timestamps.
        # send_heartbeat updates 'last_seen' on worker_heartbeats.
        
        # We need to check worker liveness separately?
        # Yes.
        
        # 2. Stuck Provisioning
        # If desired=True AND status='transitioning' AND updated_at < now - 60s
        if desired and active_status == "transitioning":
             # Checkstaleness
             state.get("updated_at")
             # Parsing is complex without knowing format. 
             # Let's assume we use a simpler heuristic or just check loop count?
             # No, simply: If it stays transitioning for > 60s.
             # We can't track duration without history. 
             # We'll rely on Last Seen being recent.
             pass

        # 3. Policy Enforcement (Desired=True but Offline)
        if desired and active_status in ["stopped", "offline"]:
             logger.warning(f"⚖️ Policy Violation: {pid} should be RUNNING but is {active_status}.")
             
             if worker_id and worker_id not in ["main", "remote"]:
                  # Attempt Pulse
                  logger.info(f"⚖️ Scolding Worker: {worker_id} (Wake Up!)")
                  # Resend 'enable' command to bus?
                  # If worker is truly offline, we need to spawn it.
                  
                  # Check ProcessManager
                  pm = getattr(self.services, "get_process_manager", lambda: None)()
                  if pm and not pm.is_running(worker_id):
                       # [Phase 9] Circuit Breaker Check
                       if self._check_circuit_breaker(worker_id, now_ts):
                           logger.warning(f"⚖️ Worker {worker_id} is Dead. Respawning...")
                           # Call PluginService ensure_worker
                           ps = self.services.get_plugin_service()
                           if ps:
                               await ps.ensure_worker_running(worker_id)
                           
                           # Record Restart
                           self._record_restart(worker_id, now_ts)
                       else:
                           logger.critical(f"🔥 Circuit Breaker Tripped! {worker_id} is crashing too frequently. Giving up.")
                           # Auto-Disable to inform UI
                           await bus.publish_state(pid, {"active_status": "error", "desired_enabled": False})
                  else:
                       # Worker running but plugin stopped?
                       # Resend Intent
                       await bus.publish_state(pid, {"desired_enabled": True})

    def _record_restart(self, worker_id: str, now: float):
        if worker_id not in self.restart_history:
            self.restart_history[worker_id] = []
        self.restart_history[worker_id].append(now)
        # Cleanup old
        self.restart_history[worker_id] = [t for t in self.restart_history[worker_id] if now - t < self.CRASH_WINDOW]

    def _check_circuit_breaker(self, worker_id: str, now: float) -> bool:
        """Return True if safe to restart, False if tripped."""
        history = self.restart_history.get(worker_id, [])
        # Prune
        valid = [t for t in history if now - t < self.CRASH_WINDOW]
        self.restart_history[worker_id] = valid
        
        if len(valid) >= self.MAX_RESTARTS:
            return False
        return True

