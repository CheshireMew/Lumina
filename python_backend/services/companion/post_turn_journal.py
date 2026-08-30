from __future__ import annotations

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import Any


POST_TURN_STEPS = (
    "history",
    "memory",
    "soul_activity",
    "soul_driver",
    "consolidation",
)


class PostTurnJournal:
    """Indexed durable operation log for post-turn effects."""

    def __init__(self, root: Path, *, completed_retention: int = 1000):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self.database_path = self.root / "post_turn.sqlite3"
        self.completed_retention = max(0, completed_retention)
        self._lock = asyncio.Lock()
        self._initialized = False
        self._connection: sqlite3.Connection | None = None

    async def begin(self, payload: dict[str, Any]) -> dict[str, Any]:
        turn_id = str(payload["turn_id"])
        if not turn_id:
            raise ValueError("turn_id is required for the post-turn journal")

        def operation(connection: sqlite3.Connection):
            existing = connection.execute(
                "SELECT payload FROM post_turn_records WHERE turn_id = ?",
                (turn_id,),
            ).fetchone()
            if existing:
                return self._decode_payload(existing["payload"])
            record = {
                **payload,
                "status": "pending",
                "steps": {step: False for step in POST_TURN_STEPS},
                "attempts": 0,
                "last_error": None,
            }
            connection.execute(
                """
                INSERT INTO post_turn_records(turn_id, status, payload)
                VALUES (?, 'pending', ?)
                """,
                (turn_id, self._encode_payload(record)),
            )
            connection.commit()
            return record

        return await self._run(operation)

    async def mark_step(self, turn_id: str, step: str) -> dict[str, Any]:
        if step not in POST_TURN_STEPS:
            raise KeyError(step)
        return await self._update(
            turn_id,
            lambda record: {
                **record,
                "status": "pending",
                "steps": {**record["steps"], step: True},
                "last_error": None,
            },
        )

    async def mark_failed(self, turn_id: str, step: str, error: Exception) -> None:
        await self._update(
            turn_id,
            lambda record: {
                **record,
                "status": "pending",
                "attempts": int(record.get("attempts") or 0) + 1,
                "last_error": {
                    "step": step,
                    "type": type(error).__name__,
                    "message": str(error),
                },
            },
        )

    async def mark_completed(self, turn_id: str) -> None:
        await self._update(
            turn_id,
            lambda record: {
                **record,
                "status": "completed",
                "last_error": None,
            },
            prune_completed=True,
        )

    async def pending(self) -> list[dict[str, Any]]:
        def operation(connection: sqlite3.Connection):
            rows = connection.execute(
                """
                SELECT payload FROM post_turn_records
                WHERE status != 'completed'
                ORDER BY updated_at ASC
                """
            ).fetchall()
            return [self._decode_payload(row["payload"]) for row in rows]

        return await self._run(operation)

    async def get(self, turn_id: str) -> dict[str, Any] | None:
        def operation(connection: sqlite3.Connection):
            row = connection.execute(
                "SELECT payload FROM post_turn_records WHERE turn_id = ?",
                (turn_id,),
            ).fetchone()
            return self._decode_payload(row["payload"]) if row else None

        return await self._run(operation)

    async def close(self) -> None:
        async with self._lock:
            connection = self._connection
            self._connection = None
            self._initialized = False
            if connection is not None:
                await asyncio.to_thread(connection.close)

    async def _update(
        self,
        turn_id: str,
        transform,
        *,
        prune_completed: bool = False,
    ) -> dict[str, Any]:
        def operation(connection: sqlite3.Connection):
            row = connection.execute(
                "SELECT payload FROM post_turn_records WHERE turn_id = ?",
                (turn_id,),
            ).fetchone()
            if row is None:
                raise KeyError(f"Post-turn record does not exist: {turn_id}")
            record = self._decode_payload(row["payload"])
            updated = transform(record)
            connection.execute(
                """
                UPDATE post_turn_records
                SET status = ?, payload = ?, updated_at = CURRENT_TIMESTAMP
                WHERE turn_id = ?
                """,
                (updated.get("status", "pending"), self._encode_payload(updated), turn_id),
            )
            if prune_completed:
                self._prune_completed(connection)
            connection.commit()
            return updated

        return await self._run(operation)

    async def _run(self, operation):
        async with self._lock:
            return await asyncio.to_thread(self._run_sync, operation)

    def _run_sync(self, operation):
        connection = self._connection
        if connection is None:
            connection = sqlite3.connect(
                self.database_path,
                timeout=15,
                check_same_thread=False,
            )
            connection.row_factory = sqlite3.Row
            connection.execute("PRAGMA busy_timeout=15000")
            connection.execute("PRAGMA synchronous=NORMAL")
            self._connection = connection
        try:
            if not self._initialized:
                self._initialize(connection)
                self._initialized = True
            return operation(connection)
        except Exception:
            connection.rollback()
            raise

    def _initialize(self, connection: sqlite3.Connection) -> None:
        connection.execute("PRAGMA journal_mode=WAL")
        connection.executescript(
            """
            CREATE TABLE IF NOT EXISTS post_turn_records (
                turn_id TEXT PRIMARY KEY,
                status TEXT NOT NULL,
                payload TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            );
            CREATE INDEX IF NOT EXISTS idx_post_turn_pending
                ON post_turn_records(status, updated_at);
            CREATE TABLE IF NOT EXISTS post_turn_metadata (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            """
        )
        imported = connection.execute(
            "SELECT value FROM post_turn_metadata WHERE key = 'legacy_json_import_v1'"
        ).fetchone()
        if imported is None:
            for path in self.root.glob("*.json"):
                try:
                    with path.open("r", encoding="utf-8") as handle:
                        record = json.load(handle)
                    if not isinstance(record, dict) or not record.get("turn_id"):
                        continue
                    connection.execute(
                        """
                        INSERT OR IGNORE INTO post_turn_records(turn_id, status, payload)
                        VALUES (?, ?, ?)
                        """,
                        (
                            str(record["turn_id"]),
                            str(record.get("status") or "pending"),
                            self._encode_payload(record),
                        ),
                    )
                except (OSError, json.JSONDecodeError):
                    continue
            connection.execute(
                "INSERT INTO post_turn_metadata(key, value) VALUES ('legacy_json_import_v1', 'complete')"
            )
        self._prune_completed(connection)
        connection.commit()

    def _prune_completed(self, connection: sqlite3.Connection) -> None:
        if self.completed_retention == 0:
            connection.execute(
                "DELETE FROM post_turn_records WHERE status = 'completed'"
            )
            return
        connection.execute(
            """
            DELETE FROM post_turn_records
            WHERE status = 'completed'
              AND turn_id NOT IN (
                  SELECT turn_id FROM post_turn_records
                  WHERE status = 'completed'
                  ORDER BY updated_at DESC, turn_id DESC
                  LIMIT ?
              )
            """,
            (self.completed_retention,),
        )

    @staticmethod
    def _encode_payload(payload: dict[str, Any]) -> str:
        return json.dumps(payload, ensure_ascii=False, separators=(",", ":"))

    @staticmethod
    def _decode_payload(payload: str) -> dict[str, Any]:
        decoded = json.loads(payload)
        if not isinstance(decoded, dict):
            raise ValueError("Invalid post-turn journal payload")
        return decoded
