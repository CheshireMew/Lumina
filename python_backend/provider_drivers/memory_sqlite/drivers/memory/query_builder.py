from typing import Any, Dict, Optional

from core.db.query_builder import QueryBuilder
from core.db.sql_identifiers import (
    sanitize_column_name,
    sanitize_order_by,
    sanitize_table_name,
)


class SQLiteQueryBuilder(QueryBuilder):
    def sanitize_table(self, table_name: str) -> str:
        return sanitize_table_name(table_name)

    def select(
        self,
        table: str,
        where: Optional[Dict[str, Any]] = None,
        limit: int = 50,
        order_by: str = "created_at DESC",
    ):
        table = self.sanitize_table(table)
        params: Dict[str, Any] = {}
        conditions = []
        for index, (key, value) in enumerate((where or {}).items(), start=1):
            column = sanitize_column_name(key)
            param = f"where_{index}"
            conditions.append(f"{column} = :{param}")
            params[param] = value

        query = f"SELECT * FROM {table}"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        order_by = sanitize_order_by(order_by)
        params["limit"] = min(max(int(limit), 1), 100)
        return f"{query} ORDER BY {order_by} LIMIT :limit", params

    def delete(self, table: str, record_id: str):
        table = self.sanitize_table(table)
        return f"DELETE FROM {table} WHERE id = :record_id", {"record_id": record_id}

    def create(self, table: str, data: Dict[str, Any]):
        table = self.sanitize_table(table)
        columns = [sanitize_column_name(key) for key in data]
        placeholders = [f":value_{index}" for index in range(len(columns))]
        params = {
            f"value_{index}": data[column]
            for index, column in enumerate(columns)
        }
        query = (
            f"INSERT INTO {table} ({', '.join(columns)}) "
            f"VALUES ({', '.join(placeholders)})"
        )
        return query, params

    def update(self, table: str, record_id: str, data: Dict[str, Any]):
        table = self.sanitize_table(table)
        sets = []
        params: Dict[str, Any] = {"record_id": record_id}
        for index, (key, value) in enumerate(data.items()):
            column = sanitize_column_name(key)
            param = f"value_{index}"
            sets.append(f"{column} = :{param}")
            params[param] = value
        return f"UPDATE {table} SET {', '.join(sets)} WHERE id = :record_id", params
