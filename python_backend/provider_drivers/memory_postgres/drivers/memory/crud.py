import logging
import re
from typing import Any, Dict, Optional

import asyncpg

from .query_builder import PostgresQueryBuilder

logger = logging.getLogger("PostgresDriver.Crud")

query_builder = PostgresQueryBuilder()


def _normalize_query(sql: str, params: Optional[Dict[str, Any]]):
    if not params:
        return sql, []

    placeholders: dict[str, int] = {}
    values: list[Any] = []

    def replace_named(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in params:
            raise ValueError(f"Missing query parameter: {name}")
        if name not in placeholders:
            placeholders[name] = len(values) + 1
            values.append(params[name])
        return f"${placeholders[name]}"

    normalized_sql = re.sub(r"\$(?!\d)([A-Za-z_][A-Za-z0-9_]*)", replace_named, sql)
    if values:
        return normalized_sql, values
    return sql, list(params.values())


async def create(pool: asyncpg.Pool, table: str, data: Dict[str, Any]) -> str:
    query, params = query_builder.create(table, data)
    normalized_query, values = _normalize_query(query, params)
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchval(normalized_query, *values)
            return str(result)
        except Exception as exc:
            logger.error("Postgres create failed for %s: %s", table, exc)
            raise


async def update(pool: asyncpg.Pool, table: str, record_id: str, data: Dict[str, Any]) -> bool:
    query, params = query_builder.update(table, record_id, data)
    normalized_query, values = _normalize_query(query, params)

    async with pool.acquire() as conn:
        try:
            await conn.execute(normalized_query, *values)
            return True
        except Exception as exc:
            logger.error("Postgres update failed for %s: %s", record_id, exc)
            raise


async def delete(pool: asyncpg.Pool, table: str, record_id: str) -> bool:
    query, params = query_builder.delete(table, record_id)
    normalized_query, values = _normalize_query(query, params)

    async with pool.acquire() as conn:
        try:
            await conn.execute(normalized_query, *values)
            return True
        except Exception as exc:
            logger.error("Postgres delete failed for %s: %s", record_id, exc)
            raise


async def query(pool: asyncpg.Pool, sql: str, params: Optional[Dict[str, Any]] = None) -> Any:
    async with pool.acquire() as conn:
        if params:
            normalized_sql, values = _normalize_query(sql, params)
            if values:
                return await conn.fetch(normalized_sql, *values)
            return await conn.fetch(sql, *params.values())
        return await conn.fetch(sql)


async def mark_memories_hit(pool: asyncpg.Pool, memory_ids: list):
    async with pool.acquire() as conn:
        try:
            await conn.execute(
                """
                UPDATE memory_items
                SET hit_count = hit_count + 1,
                    last_used_at = NOW()
                WHERE id = ANY($1::uuid[])
                """,
                [item for item in memory_ids],
            )
        except Exception as exc:
            logger.warning("Failed to mark hits: %s", exc)
