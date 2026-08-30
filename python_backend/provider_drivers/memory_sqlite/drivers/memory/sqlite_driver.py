import asyncio
import json
import math
import re
import sqlite3
import uuid
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, AsyncGenerator, Dict, Optional

import numpy as np

from core.db.query_builder import QueryBuilder
from core.interfaces.driver import BaseMemoryDriver

from .query_builder import SQLiteQueryBuilder

_TABLE_COLUMNS = {
    "conversation_turns": {
        "id",
        "session_id",
        "user_id",
        "character_id",
        "user_message",
        "assistant_message",
        "narrative",
        "embedding",
        "created_at",
        "processed_at",
        "metadata",
    },
    "memory_items": {
        "id",
        "character_id",
        "scope",
        "memory_type",
        "subject_id",
        "content",
        "summary",
        "embedding",
        "source_turn_ids",
        "confidence",
        "importance",
        "status",
        "supersedes_id",
        "hit_count",
        "created_at",
        "updated_at",
        "last_used_at",
        "metadata",
    },
    "memory_consolidation_jobs": {
        "id",
        "character_id",
        "status",
        "turn_ids",
        "error",
        "created_at",
        "updated_at",
        "metadata",
    },
}

_JSON_COLUMNS = {"embedding", "metadata", "source_turn_ids", "turn_ids"}
_NAMED_PARAMETER = re.compile(r"\$(?!\d)([A-Za-z_][A-Za-z0-9_]*)")
_VECTOR_BAND_COUNT = 8
_VECTOR_BITS_PER_BAND = 10
_VECTOR_CANDIDATE_LIMIT = 2048
_VECTOR_RECENT_FALLBACK_LIMIT = 256
_PROJECTION_CACHE: dict[int, np.ndarray] = {}


class SQLiteMemoryDriver(BaseMemoryDriver):
    """Durable, dependency-free local memory store for the desktop app."""

    def __init__(
        self,
        id: str = "driver.memory.sqlite",
        name: str = "Local SQLite",
        description: str = "Lumina-managed local conversation and memory database",
    ):
        super().__init__(id, name, description)
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()
        self._qb = SQLiteQueryBuilder()

    def get_query_builder(self) -> QueryBuilder:
        return self._qb

    async def load(self):
        await self.connect()

    async def connect(self):
        if self._connection is not None:
            return

        database_path = self._database_path()
        database_path.parent.mkdir(parents=True, exist_ok=True)
        connection = sqlite3.connect(
            database_path,
            timeout=15,
            check_same_thread=False,
        )
        connection.row_factory = sqlite3.Row
        self._connection = connection
        await self._run(self._initialize_connection)

    async def close(self):
        connection = self._connection
        if connection is None:
            return
        async with self._lock:
            await asyncio.to_thread(connection.close)
            self._connection = None

    async def initialize_schema(self):
        await self._run(self._initialize_schema_sync)

    async def create(self, table: str, data: Dict[str, Any]) -> str:
        columns = self._validated_columns(table, data)
        record_id = str(data.get("id") or uuid.uuid4())
        payload = {**data, "id": record_id}
        columns = self._validated_columns(table, payload)
        placeholders = ", ".join(f":{column}" for column in columns)
        sql = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({placeholders})"
        values = {column: self._encode(payload[column]) for column in columns}

        def operation(connection: sqlite3.Connection):
            connection.execute(sql, values)
            self._refresh_search_indexes(connection, table, record_id)
            connection.commit()

        await self._run(operation)
        return record_id

    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        columns = self._validated_columns(table, data)
        if not columns:
            return True
        assignments = ", ".join(f"{column} = :{column}" for column in columns)
        values = {column: self._encode(data[column]) for column in columns}
        values["record_id"] = id

        def operation(connection: sqlite3.Connection):
            cursor = connection.execute(
                f"UPDATE {table} SET {assignments} WHERE id = :record_id",
                values,
            )
            if cursor.rowcount > 0:
                self._refresh_search_indexes(connection, table, id)
            connection.commit()
            return cursor.rowcount > 0

        return bool(await self._run(operation))

    async def delete(self, table: str, id: str) -> bool:
        self._validated_table(table)

        def operation(connection: sqlite3.Connection):
            if table == "memory_items":
                connection.execute(
                    "DELETE FROM memory_items_fts WHERE record_id = ?",
                    (id,),
                )
            connection.execute(
                "DELETE FROM memory_vector_buckets WHERE table_name = ? AND record_id = ?",
                (table, id),
            )
            cursor = connection.execute(
                f"DELETE FROM {table} WHERE id = ?",
                (id,),
            )
            connection.commit()
            return cursor.rowcount > 0

        return bool(await self._run(operation))

    async def query(self, sql: str, params: Optional[Dict] = None) -> Any:
        normalized = self._normalize_query(sql)
        values = {key: self._encode(value) for key, value in (params or {}).items()}
        command = normalized.lstrip().split(None, 1)[0].upper()
        if command not in {"SELECT", "WITH", "UPDATE"}:
            raise ValueError(f"Unsupported SQLite memory query: {command}")

        def operation(connection: sqlite3.Connection):
            cursor = connection.execute(normalized, values)
            if command == "UPDATE":
                connection.commit()
                return []
            return [self._decode_row(row) for row in cursor.fetchall()]

        return await self._run(operation)

    async def mark_memories_hit(self, memory_ids: list):
        ids = [str(item) for item in memory_ids if item]
        if not ids:
            return
        placeholders = ", ".join("?" for _ in ids)

        def operation(connection: sqlite3.Connection):
            connection.execute(
                f"""
                UPDATE memory_items
                SET hit_count = hit_count + 1,
                    last_used_at = CURRENT_TIMESTAMP
                WHERE id IN ({placeholders})
                """,
                ids,
            )
            connection.commit()

        await self._run(operation)

    async def search_vector(
        self,
        table: str,
        vector: list,
        limit: int,
        threshold: float,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        self._validated_table(table)
        return await self._run(
            lambda connection: self._search_vector_sync(
                connection,
                table,
                vector,
                limit,
                threshold,
                filter_criteria,
            )
        )

    async def search_fulltext(
        self,
        table: str,
        query: str,
        limit: int,
        fields: list,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        self._validated_table(table)
        return await self._run(
            lambda connection: self._search_fulltext_sync(
                connection,
                table,
                query,
                limit,
                fields,
                filter_criteria,
            )
        )

    async def search_hybrid(
        self,
        query: str,
        vector: list,
        table: str,
        limit: int,
        threshold: float,
        vector_weight: float = 0.5,
        filter_criteria: Optional[Dict] = None,
    ) -> list:
        self._validated_table(table)
        return await self._run(
            lambda connection: self._search_hybrid_sync(
                connection,
                query,
                vector,
                table,
                limit,
                threshold,
                vector_weight,
                filter_criteria,
            )
        )

    async def publish(self, channel: str, message: Dict[str, Any]):
        raise NotImplementedError("SQLite memory notifications are not used by Lumina.")

    async def listen(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        raise NotImplementedError("SQLite memory notifications are not used by Lumina.")
        yield {}

    async def _filtered_rows(self, table: str, filters: Optional[Dict]) -> list[dict]:
        self._validated_table(table)
        return await self._run(
            lambda connection: self._filtered_rows_sync(connection, table, filters)
        )

    async def _run(self, operation):
        connection = self._connection
        if connection is None:
            raise RuntimeError("SQLite memory database is not connected")
        async with self._lock:
            return await asyncio.to_thread(operation, connection)

    def _database_path(self) -> Path:
        data_root_value = self.config.get("data_root")
        if not data_root_value:
            raise ValueError("SQLite memory driver requires data_root")
        data_root = Path(data_root_value).resolve()
        relative_path = Path(self.config.get("sqlite_file") or "database/lumina.sqlite3")
        if relative_path.is_absolute():
            raise ValueError("memory.sqlite_file must be relative to the Lumina data root")
        database_path = (data_root / relative_path).resolve()
        if database_path != data_root and data_root not in database_path.parents:
            raise ValueError("memory.sqlite_file must stay inside the Lumina data root")
        return database_path

    def _initialize_connection(self, connection: sqlite3.Connection):
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        self._initialize_schema_sync(connection)

    def _initialize_schema_sync(self, connection: sqlite3.Connection):
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS schema_versions (
                component TEXT PRIMARY KEY,
                version INTEGER NOT NULL,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS conversation_turns (
                id TEXT PRIMARY KEY,
                session_id INTEGER NOT NULL DEFAULT 0,
                user_id TEXT NOT NULL,
                character_id TEXT NOT NULL,
                user_message TEXT NOT NULL DEFAULT '',
                assistant_message TEXT NOT NULL DEFAULT '',
                narrative TEXT NOT NULL DEFAULT '',
                embedding TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                processed_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_turns_character_created
                ON conversation_turns(character_id, created_at DESC);
            CREATE INDEX IF NOT EXISTS idx_turns_unprocessed
                ON conversation_turns(character_id, processed_at);

            CREATE TABLE IF NOT EXISTS memory_items (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'relationship',
                memory_type TEXT NOT NULL DEFAULT 'episode',
                subject_id TEXT,
                content TEXT NOT NULL,
                summary TEXT,
                embedding TEXT,
                source_turn_ids TEXT NOT NULL DEFAULT '[]',
                confidence REAL NOT NULL DEFAULT 1.0,
                importance REAL NOT NULL DEFAULT 1.0,
                status TEXT NOT NULL DEFAULT 'active',
                supersedes_id TEXT REFERENCES memory_items(id),
                hit_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                last_used_at TEXT,
                metadata TEXT NOT NULL DEFAULT '{}'
            );
            CREATE INDEX IF NOT EXISTS idx_memory_items_character
                ON memory_items(character_id);
            CREATE INDEX IF NOT EXISTS idx_memory_items_type
                ON memory_items(memory_type);
            CREATE INDEX IF NOT EXISTS idx_memory_items_active
                ON memory_items(character_id, status);
            CREATE INDEX IF NOT EXISTS idx_memory_items_active_rank
                ON memory_items(character_id, status, importance DESC, updated_at DESC);

            CREATE TABLE IF NOT EXISTS memory_vector_buckets (
                table_name TEXT NOT NULL,
                record_id TEXT NOT NULL,
                dimension INTEGER NOT NULL,
                band INTEGER NOT NULL,
                bucket INTEGER NOT NULL,
                PRIMARY KEY (table_name, record_id, band)
            );
            CREATE INDEX IF NOT EXISTS idx_memory_vector_candidates
                ON memory_vector_buckets(table_name, dimension, band, bucket, record_id);

            CREATE TABLE IF NOT EXISTS memory_consolidation_jobs (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                turn_ids TEXT NOT NULL DEFAULT '[]',
                error TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            """
        )
        connection.execute(
            """
            CREATE VIRTUAL TABLE IF NOT EXISTS memory_items_fts
            USING fts5(record_id UNINDEXED, content, summary, tokenize='trigram')
            """
        )
        version_row = connection.execute(
            "SELECT version FROM schema_versions WHERE component = 'memory'"
        ).fetchone()
        if version_row is None or int(version_row[0]) < 3:
            self._rebuild_search_indexes(connection)
        connection.execute(
            """
            INSERT INTO schema_versions(component, version, updated_at)
            VALUES ('memory', 3, CURRENT_TIMESTAMP)
            ON CONFLICT(component) DO UPDATE SET
                version = MAX(schema_versions.version, excluded.version),
                updated_at = excluded.updated_at
            """
        )
        connection.commit()

    def _rebuild_search_indexes(self, connection: sqlite3.Connection) -> None:
        connection.execute("DELETE FROM memory_items_fts")
        connection.execute("DELETE FROM memory_vector_buckets")
        connection.execute(
            """
            INSERT INTO memory_items_fts(record_id, content, summary)
            SELECT id, content, COALESCE(summary, '') FROM memory_items
            """
        )
        for table in ("memory_items", "conversation_turns"):
            rows = connection.execute(
                f"SELECT id, embedding FROM {table} WHERE embedding IS NOT NULL"
            ).fetchall()
            indexed_rows = []
            for row in rows:
                embedding = self._decode_embedding(row["embedding"])
                if embedding:
                    indexed_rows.append((row["id"], embedding))
            self._insert_vector_buckets_batch(connection, table, indexed_rows)

    def _refresh_search_indexes(
        self,
        connection: sqlite3.Connection,
        table: str,
        record_id: str,
    ) -> None:
        if table not in {"memory_items", "conversation_turns"}:
            return
        connection.execute(
            "DELETE FROM memory_vector_buckets WHERE table_name = ? AND record_id = ?",
            (table, record_id),
        )
        row = connection.execute(
            f"SELECT * FROM {table} WHERE id = ?",
            (record_id,),
        ).fetchone()
        if row is None:
            return
        if table == "memory_items":
            connection.execute(
                "DELETE FROM memory_items_fts WHERE record_id = ?",
                (record_id,),
            )
            connection.execute(
                "INSERT INTO memory_items_fts(record_id, content, summary) VALUES (?, ?, ?)",
                (record_id, row["content"], row["summary"] or ""),
            )
        embedding = self._decode_embedding(row["embedding"])
        if embedding:
            self._insert_vector_buckets(connection, table, record_id, embedding)

    def _insert_vector_buckets(
        self,
        connection: sqlite3.Connection,
        table: str,
        record_id: str,
        vector: list,
    ) -> None:
        buckets = self._vector_buckets(vector)
        dimension = len(vector)
        connection.executemany(
            """
            INSERT OR REPLACE INTO memory_vector_buckets(
                table_name, record_id, dimension, band, bucket
            ) VALUES (?, ?, ?, ?, ?)
            """,
            [
                (table, record_id, dimension, band, bucket)
                for band, bucket in enumerate(buckets)
            ],
        )

    def _insert_vector_buckets_batch(
        self,
        connection: sqlite3.Connection,
        table: str,
        rows: list[tuple[str, list]],
    ) -> None:
        by_dimension: dict[int, list[tuple[str, list]]] = {}
        for record_id, vector in rows:
            by_dimension.setdefault(len(vector), []).append((record_id, vector))
        inserts = []
        for dimension, group in by_dimension.items():
            matrix = np.asarray([vector for _, vector in group], dtype=np.float32)
            signs = (matrix @ self._projection_matrix(dimension).T) >= 0
            for row_index, (record_id, _) in enumerate(group):
                for band in range(_VECTOR_BAND_COUNT):
                    start = band * _VECTOR_BITS_PER_BAND
                    bucket = 0
                    for bit, enabled in enumerate(
                        signs[row_index, start:start + _VECTOR_BITS_PER_BAND]
                    ):
                        if enabled:
                            bucket |= 1 << bit
                    inserts.append((table, record_id, dimension, band, bucket))
        connection.executemany(
            """
            INSERT OR REPLACE INTO memory_vector_buckets(
                table_name, record_id, dimension, band, bucket
            ) VALUES (?, ?, ?, ?, ?)
            """,
            inserts,
        )

    def _search_vector_sync(
        self,
        connection: sqlite3.Connection,
        table: str,
        vector: list,
        limit: int,
        threshold: float,
        filters: Optional[Dict],
    ) -> list:
        if not vector or limit <= 0:
            return []
        if table != "memory_items":
            rows = self._filtered_rows_sync(connection, table, filters)
            return self._rank_vector_rows(rows, vector, limit, threshold)

        filter_sql, filter_values = self._filter_clause(
            table,
            filters,
            alias="candidate_memory",
        )
        buckets = self._vector_buckets(vector)
        bucket_clauses = []
        values: dict[str, Any] = {
            "table_name": table,
            "dimension": len(vector),
            "candidate_limit": _VECTOR_CANDIDATE_LIMIT,
        }
        for band, bucket in enumerate(buckets):
            nearby = [bucket, *(
                bucket ^ (1 << bit) for bit in range(_VECTOR_BITS_PER_BAND)
            )]
            names = []
            for index, value in enumerate(nearby):
                key = f"bucket_{band}_{index}"
                values[key] = value
                names.append(f":{key}")
            bucket_clauses.append(
                f"(b.band = {band} AND b.bucket IN ({', '.join(names)}))"
            )
        values.update(filter_values)
        rows = connection.execute(
            f"""
            SELECT m.*, candidates.bucket_hits AS _bucket_hits
            FROM memory_items AS m
            JOIN (
                SELECT b.record_id, COUNT(*) AS bucket_hits
                FROM memory_vector_buckets AS b
                JOIN memory_items AS candidate_memory
                  ON candidate_memory.id = b.record_id
                WHERE b.table_name = :table_name
                  AND b.dimension = :dimension
                  AND ({' OR '.join(bucket_clauses)})
                  {filter_sql}
                GROUP BY b.record_id
                ORDER BY bucket_hits DESC
                LIMIT :candidate_limit
            ) AS candidates ON candidates.record_id = m.id
            ORDER BY candidates.bucket_hits DESC
            """,
            values,
        ).fetchall()

        recent_filter_sql, recent_values = self._filter_clause(
            table,
            filters,
            alias="m",
        )
        recent_values["fallback_limit"] = _VECTOR_RECENT_FALLBACK_LIMIT
        recent_rows = connection.execute(
            f"""
            SELECT m.* FROM memory_items AS m
            WHERE m.embedding IS NOT NULL {recent_filter_sql}
            ORDER BY m.importance DESC, m.updated_at DESC
            LIMIT :fallback_limit
            """,
            recent_values,
        ).fetchall()
        unique: dict[str, dict[str, Any]] = {}
        for row in [*rows, *recent_rows]:
            decoded = self._decode_row(row)
            unique[decoded["id"]] = decoded
        return self._rank_vector_rows(list(unique.values()), vector, limit, threshold)

    def _search_fulltext_sync(
        self,
        connection: sqlite3.Connection,
        table: str,
        query: str,
        limit: int,
        fields: list,
        filters: Optional[Dict],
    ) -> list:
        needle = query.strip()
        if not needle or limit <= 0:
            return []
        if table == "memory_items" and len(needle) >= 3:
            filter_sql, filter_values = self._filter_clause(table, filters, alias="m")
            filter_values.update({
                "fts_query": f'"{needle.replace(chr(34), chr(34) * 2)}"',
                "result_limit": limit,
            })
            rows = connection.execute(
                f"""
                SELECT m.*, bm25(memory_items_fts) AS _text_rank
                FROM memory_items_fts
                JOIN memory_items AS m ON m.id = memory_items_fts.record_id
                WHERE memory_items_fts MATCH :fts_query {filter_sql}
                ORDER BY _text_rank, m.created_at DESC
                LIMIT :result_limit
                """,
                filter_values,
            ).fetchall()
            return [{**self._decode_row(row), "score": 1.0} for row in rows]

        rows = self._filtered_rows_sync(connection, table, filters)
        selected_fields = fields or ["content"]
        folded = needle.casefold()
        results = [
            {**row, "score": 1.0}
            for row in rows
            if any(folded in str(row.get(field) or "").casefold() for field in selected_fields)
        ]
        results.sort(key=lambda item: str(item.get("created_at") or ""), reverse=True)
        return results[:limit]

    def _search_hybrid_sync(
        self,
        connection: sqlite3.Connection,
        query: str,
        vector: list,
        table: str,
        limit: int,
        threshold: float,
        vector_weight: float,
        filters: Optional[Dict],
    ) -> list:
        pool_limit = max(32, limit * 8)
        vector_rows = self._search_vector_sync(
            connection, table, vector, pool_limit, -1.0, filters
        )
        text_rows = self._search_fulltext_sync(
            connection, table, query, pool_limit, ["content", "summary"], filters
        )
        text_ids = {row["id"] for row in text_rows}
        candidates = {row["id"]: row for row in vector_rows}
        candidates.update({row["id"]: row for row in text_rows})
        scored = self._rank_vector_rows(list(candidates.values()), vector, len(candidates), -1.0)
        ranked = []
        for row in scored:
            vector_score = float(row.get("score") or 0.0)
            text_score = 1.0 if row["id"] in text_ids else 0.0
            if vector_score < threshold and text_score == 0.0:
                continue
            ranked.append({
                **row,
                "hybrid_score": vector_weight * vector_score + (1.0 - vector_weight) * text_score,
            })
        ranked.sort(key=lambda item: item["hybrid_score"], reverse=True)
        return ranked[:limit]

    def _rank_vector_rows(
        self,
        rows: list[dict[str, Any]],
        vector: list,
        limit: int,
        threshold: float,
    ) -> list:
        query = np.asarray(vector, dtype=np.float32)
        query_norm = float(np.linalg.norm(query))
        if query.ndim != 1 or not query_norm:
            return []
        valid_rows = []
        embeddings = []
        for row in rows:
            embedding = row.get("embedding")
            if isinstance(embedding, list) and len(embedding) == query.size:
                valid_rows.append(row)
                embeddings.append(embedding)
        if not embeddings:
            return []
        matrix = np.asarray(embeddings, dtype=np.float32)
        norms = np.linalg.norm(matrix, axis=1) * query_norm
        scores = np.divide(
            matrix @ query,
            norms,
            out=np.zeros(len(valid_rows), dtype=np.float32),
            where=norms > 0,
        )
        results = [
            {**row, "score": float(score)}
            for row, score in zip(valid_rows, scores)
            if float(score) >= threshold
        ]
        results.sort(key=lambda item: item["score"], reverse=True)
        return results[:limit]

    def _filtered_rows_sync(
        self,
        connection: sqlite3.Connection,
        table: str,
        filters: Optional[Dict],
    ) -> list[dict[str, Any]]:
        where, values = self._filter_clause(table, filters)
        rows = connection.execute(f"SELECT * FROM {table} WHERE 1=1 {where}", values).fetchall()
        return [self._decode_row(row) for row in rows]

    def _filter_clause(
        self,
        table: str,
        filters: Optional[Dict],
        *,
        alias: str = "",
    ) -> tuple[str, dict[str, Any]]:
        prefix = f"{alias}." if alias else ""
        conditions = []
        values: dict[str, Any] = {}
        for index, (column, value) in enumerate((filters or {}).items()):
            if column not in _TABLE_COLUMNS[table]:
                raise ValueError(f"Unknown column '{column}' for {table}")
            key = f"filter_{index}"
            conditions.append(f"{prefix}{column} = :{key}")
            values[key] = self._encode(value)
        suffix = f" AND {' AND '.join(conditions)}" if conditions else ""
        return suffix, values

    @staticmethod
    def _decode_embedding(value: Any) -> list:
        if isinstance(value, list):
            return value
        if isinstance(value, str):
            try:
                decoded = json.loads(value)
                return decoded if isinstance(decoded, list) else []
            except json.JSONDecodeError:
                return []
        return []

    @staticmethod
    def _vector_buckets(vector: list) -> list[int]:
        values = np.asarray(vector, dtype=np.float32)
        if values.ndim != 1 or values.size == 0:
            return []
        dimension = int(values.size)
        projections = SQLiteMemoryDriver._projection_matrix(dimension)
        signs = (projections @ values) >= 0
        buckets = []
        for band in range(_VECTOR_BAND_COUNT):
            start = band * _VECTOR_BITS_PER_BAND
            bucket = 0
            for bit, enabled in enumerate(signs[start:start + _VECTOR_BITS_PER_BAND]):
                if enabled:
                    bucket |= 1 << bit
            buckets.append(bucket)
        return buckets

    @staticmethod
    def _projection_matrix(dimension: int) -> np.ndarray:
        projections = _PROJECTION_CACHE.get(dimension)
        if projections is None:
            generator = np.random.default_rng(0x4C554D49 + dimension)
            projections = generator.standard_normal(
                (_VECTOR_BAND_COUNT * _VECTOR_BITS_PER_BAND, dimension),
                dtype=np.float32,
            )
            _PROJECTION_CACHE[dimension] = projections
        return projections

    def _validated_table(self, table: str) -> str:
        if table not in _TABLE_COLUMNS:
            raise ValueError(f"Unknown memory table: {table}")
        return table

    def _validated_columns(self, table: str, data: Dict[str, Any]) -> list[str]:
        self._validated_table(table)
        unknown = set(data) - _TABLE_COLUMNS[table]
        if unknown:
            raise ValueError(f"Unknown columns for {table}: {', '.join(sorted(unknown))}")
        return list(data)

    @staticmethod
    def _encode(value: Any) -> Any:
        if isinstance(value, (datetime, date)):
            return value.isoformat()
        if isinstance(value, (dict, list, tuple)):
            return json.dumps(value, ensure_ascii=False)
        if isinstance(value, bool):
            return int(value)
        return value

    @staticmethod
    def _decode_row(row: sqlite3.Row) -> dict[str, Any]:
        item = dict(row)
        for column in tuple(item):
            if column.startswith("_"):
                item.pop(column, None)
        for column in _JSON_COLUMNS.intersection(item):
            value = item.get(column)
            if isinstance(value, str):
                try:
                    item[column] = json.loads(value)
                except json.JSONDecodeError:
                    pass
        return item

    @staticmethod
    def _normalize_query(sql: str) -> str:
        normalized = sql.strip()
        if normalized.endswith(";"):
            normalized = normalized[:-1].rstrip()
        if ";" in normalized:
            raise ValueError("Multiple SQLite memory statements are not allowed")
        normalized = re.sub(r"\bNOW\(\)", "CURRENT_TIMESTAMP", normalized, flags=re.IGNORECASE)
        return _NAMED_PARAMETER.sub(r":\1", normalized)

    @staticmethod
    def _cosine_similarity(left: list, right: list) -> float:
        if not left or len(left) != len(right):
            return 0.0
        numerator = sum(float(a) * float(b) for a, b in zip(left, right))
        left_norm = math.sqrt(sum(float(value) ** 2 for value in left))
        right_norm = math.sqrt(sum(float(value) ** 2 for value in right))
        if not left_norm or not right_norm:
            return 0.0
        return numerator / (left_norm * right_norm)
