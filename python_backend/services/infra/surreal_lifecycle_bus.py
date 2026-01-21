import logging
import json
import asyncio
from typing import Any, Callable, Dict, Optional, List
from surrealdb import AsyncSurreal
from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from core.schemas import PluginState, WorkerState # [Architecture 6.1] Shared Schema
from app_config import config

logger = logging.getLogger("SurrealLifecycleBus")

class SurrealLifecycleBus(AbstractLifecycleBus):
    """
    SurrealDB Implementation of Lifecycle Bus.
    Uses 'Live Queries' for real-time updates and standard CRUD for persistence.
    """
    
    def __init__(self):
        self.db: Optional[AsyncSurreal] = None
        self.live_query_uuid = None
        self.subscribers: List[Callable] = []
        self._is_connected = False
        self._lock = asyncio.Lock() # [Architecture 5.3] Initialization Lock
        
        # Table is constant
        self.table = "plugin_state"

    def _resolve_config(self):
        """Resolve config just-in-time to avoid capturing empty values during early bootstrap."""
        self.url = config.memory.url 
        self.user = config.memory.root_user
        self.password = config.memory.root_password
        self.namespace = config.memory.namespace
        self.database = config.memory.database

    async def connect(self):
        if self._is_connected and self.db:
            return
            
        async with self._lock:
            # Re-check inside lock
            if self._is_connected and self.db:
                return

            try:
                self._resolve_config()
                if not self.namespace or not self.database:
                    raise ValueError(f"SurrealDB Namespace/Database not configured! (NS='{self.namespace}', DB='{self.database}')")

                self.db = AsyncSurreal(self.url)
                await self.db.connect()
                
                # Signin
                # [Fix] Align strictly with surreal_driver.py: 
                # 1. Use 'username'/'password'
                # 2. Separate 'use' call
                try:
                    await self.db.signin({"username": self.user, "password": self.password})
                except Exception as login_err:
                     logger.warning(f"⚠️ Configured login failed: {login_err}. Trying default root/root fallback...")
                     # Fallback strategy (mirrors surreal_driver.py)
                     await self.db.signin({"username": "root", "password": "root"})

                # Establish Context
                await self.db.use(self.namespace, self.database)
                
                # [Architecture 5.3] Context Validation
                try:
                    # In 1.x, 'INFO FOR DB' helps verify we are actually in a DB context
                    await self.db.query("INFO FOR DB;")
                except Exception as ctx_err:
                    msg = str(ctx_err)
                    if "Specify a namespace" in msg:
                        logger.critical(f"🔥 Critical: Context Switch Failed. NS={self.namespace} DB={self.database}")
                        raise RuntimeError("SurrealDB Context Switch Failed")
                    logger.warning(f"⚠️ Context check warning (ignorable if DB empty): {ctx_err}")

                logger.info(f"✅ Connected to SurrealDB Bus ({self.url}) -> NS={self.namespace}, DB={self.database}")
                self._is_connected = True
                
                # [Architecture 6.0] Schema Migration
                await self._migrate_schema()

            except Exception as e:
                logger.error(f"❌ Failed to connect to SurrealDB Bus: {e}")
                self._is_connected = False
                if self.db:
                    try:
                        await self.db.close()
                    except: pass
                    self.db = None
                # Don't raise, allow retry loop to handle it gracefully
            # We don't raise here to allow retry / fallback logic if needed
            
    async def disconnect(self):
        if self.db:
            if self.live_query_uuid:
                try:
                    await self.db.kill(self.live_query_uuid)
                except:
                    pass
            await self.db.close()
            self._is_connected = False

    async def _migrate_schema(self):
        """
        [Architecture 6.0] Schema Migration.
        Split 'enabled' into 'desired_enabled' (Intent) and 'active_status' (Reality).
        """
        try:
            # 1. Backfill desired_enabled from legacy enabled
            await self.db.query("UPDATE plugin_state SET desired_enabled = enabled WHERE desired_enabled IS NONE;")
            
            # 2. Backfill active_status
            # If enabled=true -> 'ready', else 'stopped' (Assumed for migration)
            await self.db.query("UPDATE plugin_state SET active_status = IF enabled THEN 'ready' ELSE 'stopped' END WHERE active_status IS NONE;")
            
            logger.info("✅ Schema Migration Complete")
        except Exception as e:
            logger.warning(f"Schema Migration Warning: {e}")

    async def update_plugin_state(self, state: PluginState):
        """
        [Architecture 6.1] Typed Direct Write (Scheme C).
        Workers call this directly to update their own plugin status.
        """
        # Convert pydantic model to dict, ensuring datetime serialization
        data = json.loads(state.model_dump_json())
        await self.publish_state(state.id, data)

    async def publish_state(self, plugin_id: str, state: Dict[str, Any]):
        if not self._is_connected:
            logger.warning(f"⚠️ Cannot publish state for {plugin_id}: Not Connected")
            return

        try:
            # Upsert state into 'plugin_state' table
            # ID format: plugin_state:system_voiceprint
            record_id = f"{self.table}:{plugin_id.replace('.', '_')}"
            
            data = {
                "id": record_id,
                "plugin_id": plugin_id,
                **state
            }
            
            # [Fix] Use client-side time
            import datetime
            data["last_updated"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # [Fix] Use UPSERT instead of UPDATE MERGE
            # UPSERT creates the record if it doesn't exist, otherwise updates it
            await self.db.query(f'UPSERT {record_id} CONTENT $data RETURN AFTER', {"data": data})
            logger.debug(f"💾 State Published: {plugin_id} -> status={state.get('active_status')}")
            
        except Exception as e:
            logger.error(f"❌ Failed to publish state for {plugin_id}: {e}")

    async def subscribe_state(self, callback: Callable[[str, Dict[str, Any]], Any]):
        """
        Subscribe to Live Query on 'plugin_state' table.
        """
        self.subscribers.append(callback)
        
        if self.live_query_uuid:
            # Already listening
            return

        if not self._is_connected:
            await self.connect()

        try:
            # Start Live Query
            # We want to know when ANY record in 'plugin_state' changes.
            # query = "LIVE SELECT * FROM plugin_state"
            # In Python client, we use .live(table)
            
            # NOTE: Verify Python Client API for Live Queries.
            # As of v0.3+, it returns a UUID and we receive messages via ws.
            # Handling live queries in the Python client can be tricky.
            # A common pattern is spawning a listener task.
            
            # Singleton Listener Task
            if not getattr(self, "_listening_task", None) or self._listening_task.done():
                self._listening_task = asyncio.create_task(self._listen_live())
            
        except Exception as e:
            logger.error(f"❌ Failed to initiate Live Query: {e}")

    async def _listen_live(self):
        """
        Internal loop to consume live query events.
        [Architecture 6.1] Implements Polling Fallback for reliability.
        """
        # Snapshot for change detection
        last_known_states = {}

        logger.info(f"🎧 Starting Polling Listener for {self.table}...")
        
        while True:
            try:
                if not self._is_connected:
                    await asyncio.sleep(5)
                    continue

                # Polling Interval
                await asyncio.sleep(2)

                # 1. Fetch current view
                current_states = await self.get_all_states()
                
                for pid, state in current_states.items():
                    # 2. Detect Changes
                    # We care about 'desired_enabled' (Control) and 'active_status' (Observability)
                    prev_state = last_known_states.get(pid)
                    
                    has_changed = False
                    if not prev_state:
                        has_changed = True # New plugin appeared
                    else:
                        # Check timestamp or specific fields
                        # [Optimization] Use last_updated if reliable, otherwise field compare
                        if state.get("last_updated") != prev_state.get("last_updated"):
                            has_changed = True
                        elif state.get("desired_enabled") != prev_state.get("desired_enabled"):
                            # Critical Control Signal
                            has_changed = True

                    if has_changed:
                        # 3. Notify Subscribers
                        last_known_states[pid] = state
                        
                        # Dispatch to all callbacks
                        for cb in self.subscribers:
                            try:
                                if asyncio.iscoroutinefunction(cb):
                                    await cb(pid, state)
                                else:
                                    cb(pid, state)
                            except Exception as cb_err:
                                logger.error(f"Subscriber Callback Failed for {pid}: {cb_err}")

            except asyncio.CancelledError:
                logger.info("🛑 Live Listener Cancelled")
                break
            except Exception as e:
                logger.error(f"Live Listener Error: {e}")
                await asyncio.sleep(5)
            
        # [Legacy/Unreachable] Handled by Polling until SurrealDB Py Client stabilizes Live Query
        # async for result in stream:
        #     action = result.get("action")
        #     data = result.get("result", {})
        #     
        #     plugin_id = data.get("plugin_id")
        #     if not plugin_id:
        #         continue
        #         
        #     logger.debug(f"⚡ Live Update [{action}]: {plugin_id}")
        #     
        #     # Notify subscribers
        #     for cb in self.subscribers:
        #         try:
        #             if asyncio.iscoroutinefunction(cb):
        #                 await cb(plugin_id, data)
        #             else:
        #                 cb(plugin_id, data)
        #         except Exception as e:
        #             logger.error(f"Subscriber error: {e}")
        # except Exception as e:
        #     logger.warning(f"⚠️ Live Query Interrupted: {e}. Falling back to Polling.")
        #     # Fallback to polling is implemented in get_all_states if needed, 
        #     # but here we just retry loop?
        #     await asyncio.sleep(5)
        #     # Retry connection?
        #     if self._is_connected:
        #         asyncio.create_task(self._listen_live())

    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        if not self._is_connected:
            await self.connect()
            
        try:
            # Select all records
            results = await self.db.select(self.table)
            
            # [Safety] Check result type. v1.x client returns error list/string on failure
            if not isinstance(results, list):
                logger.error(f"❌ SurrealDB returned invalid result type: {type(results)} - {results}")
                return {}

            state_map = {}
            for row in results:
                if not isinstance(row, dict):
                    continue
                pid = row.get("plugin_id")
                if pid:
                    state_map[pid] = row
            return state_map
        except Exception as e:
            logger.error(f"❌ Failed to fetch initial state: {e}")
            return {}

    async def update_worker_state(self, state: WorkerState):
        """
        [Architecture 6.1] Typed Worker Heartbeat.
        """
        if not self._is_connected: return

        try:
            record_id = f"worker_heartbeats:{state.worker_id.replace(':', '_')}"
            
            # Use model_dump for full data (host, port, load)
            data = json.loads(state.model_dump_json())
            data["id"] = record_id
            
            import datetime
            data["last_seen"] = datetime.datetime.now(datetime.timezone.utc).isoformat()

            await self.db.query(f'UPDATE {record_id} MERGE $data RETURN AFTER', {"data": data})
        except Exception as e:
            logger.debug(f"Worker State Update Error: {e}")

    async def send_heartbeat(self, worker_id: str):
        if not self._is_connected:
            return
            
        try:
            # We use a separate table 'worker_heartbeats'
            # ID: worker_heartbeats:{worker_id}
            # We just need to update 'last_seen'
            record_id = f"worker_heartbeats:{worker_id.replace(':', '_')}"
            
            data = {
                "id": record_id,
                "worker_id": worker_id
            }
            
            import datetime
            data["last_seen"] = datetime.datetime.now(datetime.timezone.utc).isoformat()
            
            # Upsert
            await self.db.query(f'UPDATE {record_id} MERGE $data RETURN AFTER', {"data": data})
            
        except Exception as e:
            # Low-level logging (debug only) to avoid spam
            logger.debug(f"Heartbeat error: {e}")

    async def get_active_workers(self, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        """Return workers seen in last X seconds"""
        if not self._is_connected:
            return []
            
        try:
            # SurrealDB time math: time::now() - 15s
            # Note: SurrealQL syntax depends on version. 
            # Safe bet: Select all and filter in Python if time math is complex, 
            # BUT efficient way is WHERE last_seen > time::now() - duration.
            
            query = f"SELECT * FROM worker_heartbeats WHERE last_seen > time::now() - {timeout_seconds}s"
            
            # Check Python client query execution
            if hasattr(self.db, "query"):
                results = await self.db.query(query)
                # Client might return nested result wrapper
                # e.g. [{'status': 'OK', 'result': [...]}]
                if isinstance(results, list) and len(results) > 0:
                   if "result" in results[0]:
                       return results[0]["result"]
                   return results # Direct list
                return []
            
            # Fallback for old client
            return await self.db.select("worker_heartbeats")
            
        except Exception as e:
            logger.error(f"Failed to get active workers: {e}")
            return []

    async def subscribe_lifecycle_shouts(self):
        """
        [Architecture 5.0] Real-time Shout Subscription.
        Yields events from the 'plugin_state' table (simulated via polling for robustness).
        """
        if not self._is_connected:
             await self.connect()
             
        # Mocking the stream for now: In a real implementation, this would use self.db.live()
        # But to avoid "str object has no attribute get" errors from unstable client live queries,
        # we implement a smart poller that yields changes.
        
        last_seen_hashes = {}
        
        while True:
            try:
                if not self._is_connected:
                     await asyncio.sleep(5)
                     try:
                         # Reconnect attempt
                         if not self._is_connected: # Double check
                             await self.connect()
                     except: pass
                     continue

                # Polling interval
                await asyncio.sleep(2)
                
                # Fetch all states
                states = await self.get_all_states() # Robust aggregated fetch
                
                for pid, state in states.items():
                    # Check for changes
                    # Simple change detection: last_updated timestamp
                    updated_at = state.get("last_updated")
                    last_updated = last_seen_hashes.get(pid)
                    
                    if updated_at != last_updated:
                        # Yield event!
                        last_seen_hashes[pid] = updated_at
                        # Convert flat state to shout event format
                        yield {
                            "worker_id": state.get("worker_id", "unknown"),
                            "plugins": [state], # Approximate: Shout usually carries full list, state is per-plugin
                            "host": state.get("host"),
                            "port": state.get("port"),
                            "capabilities": state.get("capabilities", [])
                        }

            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Shout listener error: {e}")
                await asyncio.sleep(5)
