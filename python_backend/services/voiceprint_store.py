import logging
from typing import Any

from services.infra.bus_factory import get_lifecycle_bus

logger = logging.getLogger("VoiceprintStore")

TABLE = "voiceprint_profiles"


class VoiceprintStoreUnavailable(RuntimeError):
    pass


async def _get_pool():
    bus = get_lifecycle_bus()
    try:
        return await bus.get_pool()
    except Exception as exc:
        raise VoiceprintStoreUnavailable("Voiceprint database is unavailable") from exc


async def _ensure_postgres_table(pool):
    async with pool.acquire() as conn:
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
    pool = await _get_pool()

    await _ensure_postgres_table(pool)
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            f"""
            SELECT id, name, enabled, embedding, created_at, updated_at
            FROM {TABLE}
            ORDER BY created_at DESC
            """
        )
    return [dict(row) for row in rows]


async def set_profile_enabled(name: str, enabled: bool):
    pool = await _get_pool()

    await _ensure_postgres_table(pool)
    async with pool.acquire() as conn:
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
    pool = await _get_pool()

    await _ensure_postgres_table(pool)
    async with pool.acquire() as conn:
        await conn.execute(f"DELETE FROM {TABLE} WHERE name = $1", name)


async def upsert_profile(name: str, embedding_b64: str, enabled: bool = True):
    pool = await _get_pool()

    await _ensure_postgres_table(pool)
    async with pool.acquire() as conn:
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
