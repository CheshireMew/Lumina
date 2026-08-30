import asyncio
import json
import sqlite3
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Optional

from app_config import DATA_ROOT


class LocalStateStore:
    """Shared SQLite boundary for small runtime records outside long-term memory."""

    def __init__(self, database_path: Optional[Path] = None):
        self.database_path = Path(database_path or DATA_ROOT / "database" / "lumina.sqlite3")
        self._connection: sqlite3.Connection | None = None
        self._lock = asyncio.Lock()

    @property
    def is_connected(self) -> bool:
        return self._connection is not None

    async def connect(self):
        if self._connection is not None:
            return
        async with self._lock:
            if self._connection is not None:
                return
            self.database_path.parent.mkdir(parents=True, exist_ok=True)
            connection = sqlite3.connect(
                self.database_path,
                timeout=15,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            await asyncio.to_thread(self._initialize, connection)
            self._connection = connection

    async def close(self):
        async with self._lock:
            connection = self._connection
            if connection is None:
                return
            await asyncio.to_thread(connection.close)
            self._connection = None

    async def send_heartbeat(self, worker_id: str, data: Optional[dict] = None):
        timestamp = datetime.now(timezone.utc).isoformat()
        record_id = f"worker:{worker_id.replace(':', '_')}"
        await self._execute(
            """
            INSERT INTO worker_heartbeats(id, worker_id, last_seen, data)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                worker_id = excluded.worker_id,
                last_seen = excluded.last_seen,
                data = excluded.data
            """,
            (record_id, worker_id, timestamp, json.dumps(data or {}, ensure_ascii=False)),
        )

    async def get_active_workers(self, timeout_seconds: int) -> list[dict[str, Any]]:
        cutoff = (datetime.now(timezone.utc) - timedelta(seconds=timeout_seconds)).isoformat()
        rows = await self._fetch_all(
            "SELECT * FROM worker_heartbeats WHERE last_seen > ? ORDER BY last_seen DESC",
            (cutoff,),
        )
        for row in rows:
            try:
                row["data"] = json.loads(row.get("data") or "{}")
            except json.JSONDecodeError:
                row["data"] = {}
        return rows

    async def write_audit_event(
        self,
        *,
        actor_id: str,
        action: str,
        target: str,
        status: str,
        metadata: Optional[dict] = None,
    ):
        await self._execute(
            """
            INSERT INTO security_audit(timestamp, actor_id, action, target, status, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """,
            (
                datetime.now(timezone.utc).isoformat(),
                actor_id,
                action,
                target,
                status,
                json.dumps(metadata or {}, ensure_ascii=False),
            ),
        )

    async def list_voiceprint_profiles(self) -> list[dict[str, Any]]:
        rows = await self._fetch_all(
            """
            SELECT id, name, enabled, embedding, created_at, updated_at
            FROM voiceprint_profiles
            ORDER BY created_at DESC
            """
        )
        for row in rows:
            row["enabled"] = bool(row["enabled"])
        return rows

    async def set_voiceprint_enabled(self, name: str, enabled: bool):
        await self._execute(
            """
            UPDATE voiceprint_profiles
            SET enabled = ?, updated_at = ?
            WHERE name = ?
            """,
            (int(enabled), datetime.now(timezone.utc).isoformat(), name),
        )

    async def delete_voiceprint_profile(self, name: str):
        await self._execute("DELETE FROM voiceprint_profiles WHERE name = ?", (name,))

    async def upsert_voiceprint_profile(
        self,
        name: str,
        embedding_b64: str,
        enabled: bool,
    ):
        timestamp = datetime.now(timezone.utc).isoformat()
        await self._execute(
            """
            INSERT INTO voiceprint_profiles(id, name, enabled, embedding, created_at, updated_at)
            VALUES (?, ?, ?, ?, ?, ?)
            ON CONFLICT(id) DO UPDATE SET
                name = excluded.name,
                enabled = excluded.enabled,
                embedding = excluded.embedding,
                updated_at = excluded.updated_at
            """,
            (
                f"voiceprint_profiles:{name}",
                name,
                int(enabled),
                embedding_b64,
                timestamp,
                timestamp,
            ),
        )

    async def _execute(self, sql: str, values: tuple[Any, ...] = ()):
        await self.connect()
        connection = self._require_connection()
        async with self._lock:
            def operation():
                connection.execute(sql, values)
                connection.commit()

            await asyncio.to_thread(operation)

    async def _fetch_all(
        self,
        sql: str,
        values: tuple[Any, ...] = (),
    ) -> list[dict[str, Any]]:
        await self.connect()
        connection = self._require_connection()
        async with self._lock:
            def operation():
                cursor = connection.execute(sql, values)
                return [dict(row) for row in cursor.fetchall()]

            return await asyncio.to_thread(operation)

    def _require_connection(self) -> sqlite3.Connection:
        if self._connection is None:
            raise RuntimeError("Local state store is not connected")
        return self._connection

    @staticmethod
    def _initialize(connection: sqlite3.Connection):
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA synchronous=NORMAL")
        connection.execute("PRAGMA foreign_keys=ON")
        connection.execute("PRAGMA busy_timeout=15000")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS worker_heartbeats (
                id TEXT PRIMARY KEY,
                worker_id TEXT NOT NULL,
                last_seen TEXT NOT NULL,
                data TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS security_audit (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                actor_id TEXT NOT NULL,
                action TEXT NOT NULL,
                target TEXT NOT NULL,
                status TEXT NOT NULL,
                metadata TEXT NOT NULL DEFAULT '{}'
            );

            CREATE TABLE IF NOT EXISTS voiceprint_profiles (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                enabled INTEGER NOT NULL DEFAULT 1,
                embedding TEXT NOT NULL,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL
            );
            """
        )
        connection.commit()


_store: LocalStateStore | None = None


def get_local_state_store() -> LocalStateStore:
    global _store
    if _store is None:
        _store = LocalStateStore()
    return _store
