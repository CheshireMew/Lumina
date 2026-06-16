import datetime as dt
import logging
from typing import Any

from services.infra.bus_factory import get_lifecycle_bus

logger = logging.getLogger("VoiceprintStore")

TABLE = "voiceprint_profiles"


class VoiceprintStoreUnavailable(RuntimeError):
    pass


async def _get_db():
    bus = get_lifecycle_bus()
    db = await bus.get_pool()
    if db is None:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable")
    return db


async def _ensure_postgres_table(db):
    async with db.acquire() as conn:
        await conn.execute(
            f"""
            CREATE TABLE IF NOT EXISTS {TABLE} (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL UNIQUE,
                enabled BOOLEAN DEFAULT TRUE,
                embedding TEXT NOT NULL,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )


async def list_profiles() -> list[dict[str, Any]]:
    db = await _get_db()

    if hasattr(db, "select"):
        results = await db.select(TABLE)
        return results if isinstance(results, list) else []

    await _ensure_postgres_table(db)
    async with db.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, name, enabled, embedding, created_at, updated_at
            FROM {TABLE}
            ORDER BY created_at DESC
            """
        )
    return [dict(row) for row in rows]


async def set_profile_enabled(name: str, enabled: bool):
    db = await _get_db()

    if hasattr(db, "query"):
        record_id = f"{TABLE}:{name}"
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        await db.query(
            f"UPDATE {record_id} SET enabled = $enabled, updated_at = $now",
            {"enabled": enabled, "now": now},
        )
        return

    await _ensure_postgres_table(db)
    async with db.acquire() as conn:
        await conn.execute(
            f"""
            UPDATE {TABLE}
            SET enabled = $1, updated_at = NOW()
            WHERE name = $2
            """,
            enabled,
            name,
        )


async def delete_profile(name: str):
    db = await _get_db()

    if hasattr(db, "delete") and hasattr(db, "query"):
        await db.delete(f"{TABLE}:{name}")
        return

    await _ensure_postgres_table(db)
    async with db.acquire() as conn:
        await conn.execute(f"DELETE FROM {TABLE} WHERE name = $1", name)


async def upsert_profile(name: str, embedding_b64: str, enabled: bool = True):
    db = await _get_db()

    if hasattr(db, "query"):
        record_id = f"{TABLE}:{name}"
        now = dt.datetime.now(dt.timezone.utc).isoformat()
        data = {
            "id": record_id,
            "name": name,
            "enabled": enabled,
            "embedding": embedding_b64,
            "created_at": now,
            "updated_at": now,
        }
        await db.query(f"UPDATE {record_id} MERGE $data", {"data": data})
        return

    await _ensure_postgres_table(db)
    async with db.acquire() as conn:
        await conn.execute(
            f"""
            INSERT INTO {TABLE} (id, name, enabled, embedding, created_at, updated_at)
            VALUES ($1, $2, $3, $4, NOW(), NOW())
            ON CONFLICT (id) DO UPDATE SET
                name = EXCLUDED.name,
                enabled = EXCLUDED.enabled,
                embedding = EXCLUDED.embedding,
                updated_at = NOW()
            """,
            f"{TABLE}:{name}",
            name,
            enabled,
            embedding_b64,
        )
