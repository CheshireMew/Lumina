import logging
from typing import Any, Dict, Optional

import asyncpg

from core.db.sql_identifiers import sanitize_column_name, sanitize_table_name

logger = logging.getLogger("PostgresDriver.Search")


async def search_vector(
    pool: asyncpg.Pool,
    table: str,
    vector: list,
    limit: int,
    threshold: float,
    filter_criteria: Optional[Dict] = None,
) -> list:
    table = sanitize_table_name(table)

    async with pool.acquire() as conn:
        where_clauses = []
        params = [vector]
        idx = 2

        if filter_criteria:
            for key, value in filter_criteria.items():
                sanitize_column_name(key)
                where_clauses.append(f"{key} = ${idx}")
                params.append(value)
                idx += 1

        where_sql = " AND ".join(where_clauses)
        where_sql = f"WHERE {where_sql} AND" if where_sql else "WHERE"

        query = f"""
            SELECT *, (1 - (embedding <=> $1)) as score
            FROM {table}
            {where_sql} (1 - (embedding <=> $1)) >= ${idx}
            ORDER BY score DESC
            LIMIT ${idx + 1}
        """
        params.extend([threshold, limit])

        try:
            rows = await conn.fetch(query, *params)
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("Postgres vector search failed: %s", exc)
            return []


async def search_fulltext(
    pool: asyncpg.Pool,
    table: str,
    query: str,
    limit: int,
    fields: list,
    filter_criteria: Optional[Dict] = None,
) -> list:
    table = sanitize_table_name(table)

    async with pool.acquire() as conn:
        where_clauses = []
        params = [query]
        idx = 2

        if filter_criteria:
            for key, value in filter_criteria.items():
                sanitize_column_name(key)
                where_clauses.append(f"{key} = ${idx}")
                params.append(value)
                idx += 1

        search_field = fields[0] if fields else "content"
        sanitize_column_name(search_field)

        where_sql = " AND ".join(where_clauses)
        where_sql = f"WHERE {where_sql} AND" if where_sql else "WHERE"

        sql = f"""
            SELECT *, 1.0 as score
            FROM {table}
            {where_sql} {search_field} ILIKE ${idx}
            ORDER BY created_at DESC
            LIMIT ${idx + 1}
        """
        params.extend([f"%{query}%", limit])

        try:
            rows = await conn.fetch(sql, *params)
            return [dict(row) for row in rows]
        except Exception as exc:
            logger.error("Postgres fulltext search failed: %s", exc)
            return []


async def search_hybrid(
    pool: asyncpg.Pool,
    query: str,
    vector: list,
    table: str,
    limit: int,
    threshold: float,
    vector_weight: float = 0.5,
    filter_criteria: Optional[Dict] = None,
) -> list:
    vec_results = await search_vector(
        pool, table, vector, limit * 2, threshold, filter_criteria
    )
    text_results = await search_fulltext(
        pool, table, query, limit * 2, ["content"], filter_criteria
    )

    scores: Dict[str, float] = {}
    items: Dict[str, Dict[str, Any]] = {}
    k = 60

    def process_list(rows, weight):
        for rank, item in enumerate(rows):
            item_id = str(item.get("id"))
            if not item_id:
                continue

            if item_id not in scores:
                scores[item_id] = 0.0
                items[item_id] = item

            scores[item_id] += weight / (k + rank + 1)

    process_list(vec_results, vector_weight)
    process_list(text_results, 1.0 - vector_weight)

    sorted_ids = sorted(scores.keys(), key=lambda item_id: scores[item_id], reverse=True)
    results = []
    for item_id in sorted_ids[:limit]:
        item = items[item_id]
        item["hybrid_score"] = scores[item_id]
        results.append(item)

    return results
