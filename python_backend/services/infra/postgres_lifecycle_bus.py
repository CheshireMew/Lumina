import logging
import json
import asyncio
from typing import Any, Dict, Optional, List
from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from core.schemas import WorkerState
from app_config import config

logger = logging.getLogger("PostgresLifecycleBus")


def _load_asyncpg():
    import asyncpg

    return asyncpg

class PostgresLifecycleBus(AbstractLifecycleBus):
    """
    PostgreSQL Implementation of Lifecycle Bus.
    Uses 'LISTEN/NOTIFY' for real-time updates and standard SQL for persistence.
    """
    
    def __init__(self):
        self._pool: Optional[Any] = None
        self._listener_conn: Optional[Any] = None
        self._is_connected = False
        self._lock = asyncio.Lock()
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
                asyncpg = _load_asyncpg()
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
                
                logger.info(f"✅ Connected to PostgreSQL Bus at {pg_config.host}:{pg_config.port}")
                self._is_connected = True
            except Exception as e:
                logger.error(f"❌ Failed to connect to PostgreSQL Bus: {e}")
                await self._close_resources()
                raise

    async def _ensure_connected(self):
        if not self._is_connected or not self._pool:
            await self.connect()
        if not self._pool:
            raise RuntimeError("PostgreSQL lifecycle bus is not connected")

    async def _initialize_schema(self):
        async with self._pool.acquire() as conn:
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS worker_heartbeats (
                    id TEXT PRIMARY KEY,
                    worker_id TEXT NOT NULL,
                    last_seen TIMESTAMPTZ DEFAULT NOW(),
                    data JSONB DEFAULT '{}'
                );
            """)

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
        await self._close_resources()

    async def _close_resources(self):
        self._is_connected = False
        if self._listener_conn:
            await self._listener_conn.close()
            self._listener_conn = None
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def get_pool(self):
        await self._ensure_connected()
        return self._pool

    async def update_worker_state(self, state: WorkerState):
        """Typed heartbeat update"""
        await self.send_heartbeat(state.worker_id, data=json.loads(state.model_dump_json()))

    async def send_heartbeat(self, worker_id: str, data: Optional[Dict] = None):
        await self._ensure_connected()

        async with self._pool.acquire() as conn:
            record_id = f"worker:{worker_id.replace(':', '_')}"
            await conn.execute("""
                INSERT INTO worker_heartbeats (id, worker_id, last_seen, data)
                VALUES ($1, $2, NOW(), $3)
                ON CONFLICT (id) DO UPDATE SET
                    last_seen = NOW(),
                    data = EXCLUDED.data
            """, record_id, worker_id, json.dumps(data or {}))

    async def get_active_workers(self, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        await self._ensure_connected()

        async with self._pool.acquire() as conn:
            rows = await conn.fetch("""
                SELECT * FROM worker_heartbeats
                WHERE last_seen > NOW() - (interval '1 second' * $1)
            """, timeout_seconds)
            return [dict(row) for row in rows]

