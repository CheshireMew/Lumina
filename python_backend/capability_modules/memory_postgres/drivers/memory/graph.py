import logging
import json
from typing import Dict, Optional

import asyncpg

logger = logging.getLogger("PostgresDriver.Graph")


async def relate(
    pool: asyncpg.Pool,
    subject: str,
    predicate: str,
    object: str,
    data: Optional[Dict] = None,
) -> bool:
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                "INSERT INTO entities (id, name, type) VALUES ($1, $1, 'auto') ON CONFLICT DO NOTHING",
                subject,
            )
            await conn.execute(
                "INSERT INTO entities (id, name, type) VALUES ($1, $1, 'auto') ON CONFLICT DO NOTHING",
                object,
            )
            await conn.execute(
                """
                INSERT INTO relations (subject_id, predicate, object_id, data)
                VALUES ($1, $2, $3, $4)
                """,
                subject,
                predicate,
                object,
                json.dumps(data or {}),
            )
            return True
        except Exception as exc:
            logger.error("Postgres relate failed: %s", exc)
            return False


async def get_neighbors(pool: asyncpg.Pool, node_id: str, depth: int = 1) -> list:
    async with pool.acquire() as conn:
        try:
            rows = await conn.fetch(
                """
                SELECT r.predicate, e.id, e.name, e.type, e.metadata
                FROM relations r
                JOIN entities e ON r.object_id = e.id
                WHERE r.subject_id = $1
                """,
                node_id,
            )
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("Postgres graph query failed: %s", exc)
            return []
