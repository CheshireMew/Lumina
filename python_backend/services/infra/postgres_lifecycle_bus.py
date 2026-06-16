import logging
import json
import asyncio
from typing import Any, Callable, Dict, Optional, List, Awaitable
import asyncpg
from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from core.schemas import PluginState, WorkerState
from app_config import config

logger = logging.getLogger("PostgresLifecycleBus")

class PostgresLifecycleBus(AbstractLifecycleBus):
    """
    PostgreSQL Implementation of Lifecycle Bus.
    Uses 'LISTEN/NOTIFY' for real-time updates and standard SQL for persistence.
    """
    
    def __init__(self):
        self._pool: Optional[asyncpg.Pool] = None
        self._listener_conn: Optional[asyncpg.Connection] = None
        self.subscribers: List[Callable] = []
        self._is_connected = False
        self._lock = asyncio.Lock()
        self._listener_task: Optional[asyncio.Task] = None
        
        # Channel for NOTIFY
        self.channel = "lumina_lifecycle_events"
        logger.info("🆕 PostgresLifecycleBus Instance Created")

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    async def connect(self):
        if self._is_connected and self._pool:
            return
            
        async with self._lock:
            if self._is_connected and self._pool:
                return

            try:
                pg_config = config.memory.postgres
                self._pool = await asyncpg.create_pool(
                    user=pg_config.user,
                    password=pg_config.password,
                    database=pg_config.database,
                    host=pg_config.host,
                    port=pg_config.port,
                    min_size=1,
                    max_size=5
                )
                
                # Ensure Schema
                await self._initialize_schema()
                
                # Start Listener on a DEDICATED connection (not from pool)
                self._listener_conn = await asyncpg.connect(
                    user=pg_config.user,
                    password=pg_config.password,
                    database=pg_config.database,
                    host=pg_config.host,
                    port=pg_config.port
                )
                self._listener_task = asyncio.create_task(self._listen_loop())
                
                logger.info(f"✅ Connected to PostgreSQL Bus at {pg_config.host}:{pg_config.port}")
                self._is_connected = True
            except Exception as e:
                logger.error(f"❌ Failed to connect to PostgreSQL Bus: {e}")
                self._is_connected = False
                if self._pool:
                    await self._pool.close()
                    self._pool = None
                if self._listener_conn:
                    await self._listener_conn.close()
                    self._listener_conn = None

    async def _initialize_schema(self):
        async with self._pool.acquire() as conn:
            # 1. Plugin State
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS plugin_state (
                    id TEXT PRIMARY KEY,
                    plugin_id TEXT NOT NULL,
                    desired_enabled BOOLEAN,
                    active_status TEXT,
                    last_updated TIMESTAMPTZ DEFAULT NOW(),
                    data JSONB DEFAULT '{}'
                );
            """)
            
            # 2. Worker Heartbeats
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    last_seen TIMESTAMPTZ DEFAULT NOW(),
                    data JSONB DEFAULT '{}'
                );
            """)

            # 3. Security Audit
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS security_audit (
                    id SERIAL PRIMARY KEY,
                    timestamp TIMESTAMPTZ DEFAULT NOW(),
                    actor_id TEXT NOT NULL,
                    action TEXT NOT NULL,
                    target TEXT NOT NULL,
                    status TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}'
                );
            """)

    async def disconnect(self):
        if self._listener_task:
            self._listener_task.cancel()
        if self._listener_conn:
            await self._listener_conn.close()
            self._listener_conn = None
        if self._pool:
            await self._pool.close()
            self._pool = None
            self._is_connected = False

    async def get_pool(self):
        if not self._is_connected:
            await self.connect()
        return self._pool

    async def update_plugin_state(self, state: PluginState):
        """Typed wrapper for publish_state"""
        data = json.loads(state.model_dump_json())
        await self.publish_state(state.id, data)

    async def publish_state(self, plugin_id: str, state: Dict[str, Any]):
        if not self._is_connected: return

        async with self._pool.acquire() as conn:
            try:
                record_id = f"plugin_state:{plugin_id.replace('.', '_')}"
                
                # Standard fields
                desired_enabled = state.get("desired_enabled")
                active_status = state.get("active_status")
                
                # Upsert with Smart Intent Protection (COALESCE)
                # If desired_enabled is provided (by Controller), update it.
                # If not provided (by Worker), keep existing value.
                # Helper for JSON serialization
                def json_serializer(o):
                    if hasattr(o, "model_dump"): return o.model_dump()
                    if hasattr(o, "dict"): return o.dict()
                    if hasattr(o, "value"): return o.value
                    return str(o)

                await conn.execute("""
                    INSERT INTO plugin_state (id, plugin_id, desired_enabled, active_status, last_updated, data)
                    VALUES ($1, $2, $3, $4, NOW(), $5)
                    ON CONFLICT (id) DO UPDATE SET 
                        desired_enabled = COALESCE(EXCLUDED.desired_enabled, plugin_state.desired_enabled),
                        active_status = EXCLUDED.active_status,
                        last_updated = NOW(),
                        data = EXCLUDED.data
                """, record_id, plugin_id, desired_enabled, active_status, json.dumps(state, default=json_serializer))
                
                # Notify
                payload = json.dumps({"plugin_id": plugin_id, "state": state}, default=json_serializer)
                await conn.execute(f"SELECT pg_notify($1, $2)", self.channel, payload)
                
                logger.debug(f"💾 State Published (Postgres): {plugin_id}")
            except Exception as e:
                logger.error(f"❌ Failed to publish state to Postgres: {e}")

    async def subscribe_state(self, callback: Callable[[str, Dict[str, Any]], Awaitable[None]]):
        self.subscribers.append(callback)
        if not self._is_connected:
            await self.connect()

    async def get_all_states(self) -> Dict[str, Dict[str, Any]]:
        if not self._is_connected:
            await self.connect()
            
        async with self._pool.acquire() as conn:
            try:
                rows = await conn.fetch("SELECT plugin_id, desired_enabled, data FROM plugin_state")
                result = {}
                for row in rows:
                    data = json.loads(row['data'])
                    # [Fix] Enforce Column Authority for Intent
                    # If column has value, it overrides/augments the JSON blob
                    if row['desired_enabled'] is not None:
                        data['desired_enabled'] = row['desired_enabled']
                    result[row['plugin_id']] = data
                return result
            except Exception as e:
                logger.error(f"❌ Failed to fetch states from Postgres: {e}")
                return {}

    async def update_worker_state(self, state: WorkerState):
        """Typed heartbeat update"""
        await self.send_heartbeat(state.worker_id, data=json.loads(state.model_dump_json()))

    async def send_heartbeat(self, worker_id: str, data: Optional[Dict] = None):
        if not self._is_connected: return
        
        async with self._pool.acquire() as conn:
            try:
                record_id = f"worker:{worker_id.replace(':', '_')}"
                await conn.execute("""
                    INSERT INTO worker_heartbeats (id, worker_id, last_seen, data)
                    VALUES ($1, $2, NOW(), $3)
                    ON CONFLICT (id) DO UPDATE SET 
                        last_seen = NOW(),
                        data = EXCLUDED.data
                """, record_id, worker_id, json.dumps(data or {}))
            except Exception as e:
                logger.debug(f"Heartbeat error: {e}")

    async def get_active_workers(self, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        if not self._is_connected: return []
        
        async with self._pool.acquire() as conn:
            try:
                rows = await conn.fetch("""
                    SELECT * FROM worker_heartbeats 
                    WHERE last_seen > NOW() - (interval '1 second' * $1)
                """, timeout_seconds)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Failed to get active workers: {e}")
                return []

    async def _listen_loop(self):
        """Persistent connection for LISTEN"""
        try:
            def callback(connection, pid, channel, payload):
                try:
                    data = json.loads(payload)
                    plugin_id = data.get("plugin_id")
                    state = data.get("state")
                    if plugin_id and state:
                        for cb in self.subscribers:
                            asyncio.create_task(cb(plugin_id, state))
                except Exception as e:
                    logger.error(f"Error in bus callback: {e}")

            await self._listener_conn.add_listener(self.channel, callback)
            logger.info(f"🎧 Listening on channel: {self.channel} (Dedicated Conn)")
            
            while True:
                await asyncio.sleep(60) 
        except asyncio.CancelledError:
            pass
        except Exception as e:
            logger.error(f"Bus listener error: {e}")
