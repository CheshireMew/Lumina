import re
from typing import Any, Optional

from memory.core import MemoryService
from services.companion.context import CompanionContextResolver


INSPECTION_TABLES = {
    "memory_items": "Single source of long-term memories",
    "conversation_turns": "Raw conversation turns",
    "memory_consolidation_jobs": "Pending and completed memory consolidation work",
}


def list_inspection_tables() -> dict[str, Any]:
    return {
        "tables": [
            {"name": name, "info": info}
            for name, info in INSPECTION_TABLES.items()
        ]
    }


def serialize_value(value: Any) -> Any:
    if isinstance(value, (str, int, float, bool, list, dict, type(None))):
        return value
    return str(value)


def serialize_rows(rows: Any) -> list[dict[str, Any]]:
    if not rows:
        return []

    serialized: list[dict[str, Any]] = []
    for record in rows:
        if hasattr(record, "keys"):
            row = {key: serialize_value(record[key]) for key in record.keys()}
        elif isinstance(record, dict):
            row = {key: serialize_value(value) for key, value in record.items()}
        else:
            row = {"value": serialize_value(record)}
        serialized.append(row)
    return serialized


def serialize_memory_rows(rows: list[dict[str, Any]], score_key: str) -> list[dict[str, Any]]:
    return [
        {
            "id": str(row.get("id", "")),
            "content": row.get("content", row.get("narrative", "")),
            "score": serialize_value(row.get(score_key, 0)),
            "created_at": serialize_value(row.get("created_at", "")),
            "importance": serialize_value(row.get("importance", 1)),
            "memory_type": row.get("memory_type", ""),
            "scope": row.get("scope", ""),
        }
        for row in rows
    ]


class MemoryInspectionService:
    def __init__(
        self,
        memory_service: MemoryService,
        context_resolver: CompanionContextResolver,
    ):
        self._memory = memory_service
        self._context_resolver = context_resolver

    async def overview(self, character_id: Optional[str] = None) -> dict[str, Any]:
        cid = self._resolve_character_id(character_id)
        turns = await self._query(
            "SELECT * FROM conversation_turns WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        memories = await self._query(
            "SELECT * FROM memory_items WHERE character_id = $cid ORDER BY created_at DESC LIMIT 100;",
            {"cid": cid},
        )
        return {"status": "success", "turns": turns, "memories": memories}

    async def processing_status(self, character_id: Optional[str] = None) -> dict[str, Any]:
        cid = self._resolve_character_id(character_id)
        conversations = await self._query(
            "SELECT count(*) AS count FROM conversation_turns WHERE character_id = $cid;",
            {"cid": cid},
        )
        unprocessed = await self._query(
            "SELECT count(*) AS count FROM conversation_turns WHERE character_id = $cid AND processed_at IS NULL;",
            {"cid": cid},
        )
        memories = await self._query(
            "SELECT count(*) AS count FROM memory_items WHERE character_id = $cid;",
            {"cid": cid},
        )

        pending_conversations = self._count(unprocessed)
        total_memories = self._count(memories)
        threshold = 20

        return {
            "status": "success",
            "turns": {
                "unprocessed": pending_conversations,
                "total": self._count(conversations),
                "threshold": threshold,
                "progress_percent": min(100, int((pending_conversations / threshold) * 100)) if threshold else 0,
            },
            "memories": {
                "active": {"unconsolidated": 0, "total": total_memories, "threshold": threshold, "progress_percent": 0},
            },
        }

    def list_tables(self) -> dict[str, Any]:
        return list_inspection_tables()

    async def table_rows(
        self,
        table_name: str,
        *,
        limit: int = 50,
        character_id: Optional[str] = None,
    ) -> dict[str, Any]:
        qb = self._memory.driver.get_query_builder()
        where_clause = {"character_id": character_id} if character_id else None
        query, params = qb.select(table_name, where=where_clause, limit=limit)
        rows = await self._memory.driver.query(query, params)
        return {"status": "success", "data": serialize_rows(rows)}

    async def select_query(self, query: str) -> dict[str, Any]:
        self._validate_select_query(query)
        rows = await self._memory.driver.query(query)
        return {"status": "success", "result": serialize_rows(rows)}

    async def delete_record(self, table_name: str, record_id: str) -> dict[str, Any]:
        self._ensure_content_table(table_name)
        await self._memory.driver.delete(table_name, record_id)
        return {"status": "success", "id": record_id}

    async def create_record(self, table_name: str, data: dict[str, Any]) -> dict[str, Any]:
        self._ensure_content_table(table_name)
        new_id = await self._memory.driver.create(table_name, data)
        return {"status": "success", "id": new_id}

    async def update_record(
        self,
        table_name: str,
        record_id: str,
        data: dict[str, Any],
    ) -> dict[str, Any]:
        self._ensure_content_table(table_name)
        safe_data = data.copy()
        for key in ["id", "created_at", "uuid"]:
            safe_data.pop(key, None)
        await self._memory.driver.update(table_name, record_id, safe_data)
        return {"status": "success"}

    async def _query(self, sql: str, params: dict | None = None) -> list[dict[str, Any]]:
        rows = await self._memory.driver.query(sql, params or {})
        return serialize_rows(rows)

    def _resolve_character_id(self, character_id: Optional[str]) -> str:
        return self._context_resolver.resolve(character_id=character_id).character_id.lower()

    @staticmethod
    def _count(rows: list[dict[str, Any]]) -> int:
        if not rows:
            return 0
        return int(rows[0].get("total") or rows[0].get("count") or 0)

    @staticmethod
    def _validate_select_query(query: str) -> None:
        normalized_query = query.strip().upper()
        if ";" in normalized_query:
            raise ValueError("Multiple statements are not allowed.")

        forbidden_pattern = r"\b(DELETE|UPDATE|INSERT|CREATE|DROP|ALTER|GRANT|REVOKE|TRUNCATE|REPLACE)\b"
        if re.search(forbidden_pattern, normalized_query):
            raise PermissionError("Only SELECT queries are allowed.")

        if not normalized_query.startswith("SELECT"):
            raise ValueError("Query must start with SELECT.")

    @staticmethod
    def _ensure_content_table(table_name: str) -> None:
        if not table_name.replace("_", "").isalnum():
            raise ValueError("Invalid table name")
        if table_name not in INSPECTION_TABLES:
            raise PermissionError(f"Inspection writes are not allowed for table '{table_name}'")
