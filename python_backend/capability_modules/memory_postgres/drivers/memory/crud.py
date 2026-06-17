import logging
import re
from typing import Any, Dict, Optional

import asyncpg

from .sql_utils import sanitize_column_name, sanitize_table_name

logger = logging.getLogger("PostgresDriver.Crud")


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
    table = sanitize_table_name(table)

    columns = []
    placeholders = []
    values = []

    idx = 1
    for key, value in data.items():
        sanitize_column_name(key)
        columns.append(key)
        placeholders.append(f"${idx}")
        values.append(value)
        idx += 1

    query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
    async with pool.acquire() as conn:
        try:
            result = await conn.fetchval(query, *values)
            return str(result)
        except Exception as exc:
            logger.error("Postgres create failed for %s: %s", table, exc)
            raise


async def update(pool: asyncpg.Pool, table: str, record_id: str, data: Dict[str, Any]) -> bool:
    table = sanitize_table_name(table)

    sets = []
    values = []
    idx = 1
    for key, value in data.items():
        sanitize_column_name(key)
        sets.append(f"{key} = ${idx}")
        values.append(value)
        idx += 1

    values.append(record_id)
    query = f"UPDATE {table} SET {', '.join(sets)} WHERE id = ${idx}"

    async with pool.acquire() as conn:
        try:
            await conn.execute(query, *values)
            return True
        except Exception as exc:
            logger.error("Postgres update failed for %s: %s", record_id, exc)
            return False


async def delete(pool: asyncpg.Pool, table: str, record_id: str) -> bool:
    table = sanitize_table_name(table)

    async with pool.acquire() as conn:
        try:
            await conn.execute(f"DELETE FROM {table} WHERE id = $1", record_id)
            return True
        except Exception as exc:
            logger.error("Postgres delete failed for %s: %s", record_id, exc)
            return False


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
                UPDATE episodic_memory
                SET hit_count = hit_count + 1,
                    last_hit_at = NOW()
                WHERE id = ANY($1::uuid[])
                """,
                [item for item in memory_ids],
            )
        except Exception as exc:
            logger.warning("Failed to mark hits: %s", exc)
