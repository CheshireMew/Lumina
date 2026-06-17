import asyncio
import json
import logging
from typing import Any, Dict, AsyncGenerator

import asyncpg

logger = logging.getLogger("PostgresDriver.Notifications")


async def publish(pool: asyncpg.Pool, channel: str, message: Dict[str, Any]):
    async with pool.acquire() as conn:
        try:
            await conn.execute("SELECT pg_notify($1, $2)", channel, json.dumps(message))
        except Exception as exc:
            logger.error("Postgres publish failed: %s", exc)


async def listen(pool: asyncpg.Pool, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
    queue = asyncio.Queue()

    def callback(connection, pid, ch, payload):
        try:
            queue.put_nowait(json.loads(payload))
        except Exception:
            pass

    conn = await pool.acquire()
    try:
        await conn.add_listener(channel, callback)
        while True:
            yield await queue.get()
    finally:
        await conn.remove_listener(channel, callback)
        await pool.release(conn)
