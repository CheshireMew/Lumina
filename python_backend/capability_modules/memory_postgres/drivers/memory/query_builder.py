from typing import Any, Dict, Optional

from core.db.query_builder import QueryBuilder

from .sql_utils import sanitize_column_name, sanitize_order_by, sanitize_table_name


class PostgresQueryBuilder(QueryBuilder):
    def sanitize_table(self, table_name: str) -> str:
        return sanitize_table_name(table_name)

    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        order_by: str = "created_at DESC",
    ):
        table = sanitize_table_name(table)

        query = f"SELECT * FROM {table}"
        params: Dict[str, Any] = {}
        conditions = []

        if where:
            idx = 1
            for key, value in where.items():
                sanitize_column_name(key)
                conditions.append(f"{key} = ${idx}")
                params[f"p_{idx}"] = value
                idx += 1

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        order_by = sanitize_order_by(order_by)
        limit_idx = len(params) + 1
        query += f" ORDER BY {order_by} LIMIT ${limit_idx};"
        params["limit"] = min(limit, 100)
        return query, params

    def delete(self, table: str, record_id: str):
        table = sanitize_table_name(table)
        query = f"DELETE FROM {table} WHERE id = $1;"
        return query, {"id": record_id}

    def create(self, table: str, data: Dict[str, Any]):
        table = sanitize_table_name(table)
        columns = []
        placeholders = []
        params: Dict[str, Any] = {}
        idx = 1
        for key, value in data.items():
            sanitize_column_name(key)
            columns.append(key)
            placeholders.append(f"${idx}")
            params[f"p_{idx}"] = value
            idx += 1

        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)}) RETURNING id;"
        )
        return query, params

    def update(self, table: str, record_id: str, data: Dict[str, Any]):
        table = sanitize_table_name(table)
        sets = []
        params: Dict[str, Any] = {}
        idx = 1
        for key, value in data.items():
            sanitize_column_name(key)
            sets.append(f"{key} = ${idx}")
            params[f"p_{idx}"] = value
            idx += 1

        query = f"UPDATE {table} SET {', '.join(sets)} WHERE id = ${idx};"
        params["id_final"] = record_id
        return query, params
