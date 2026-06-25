import logging

import asyncpg

logger = logging.getLogger("PostgresDriver.Schema")


async def initialize_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
        await conn.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto;")

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_turns (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                session_id INTEGER NOT NULL DEFAULT 0,
                user_id TEXT NOT NULL,
                character_id TEXT NOT NULL,
                user_message TEXT NOT NULL DEFAULT '',
                assistant_message TEXT NOT NULL DEFAULT '',
                narrative TEXT NOT NULL DEFAULT '',
                embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                processed_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'
            );
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_turns_character_created ON conversation_turns(character_id, created_at DESC);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_turns_unprocessed ON conversation_turns(character_id, processed_at) WHERE processed_at IS NULL;"
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_items (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                character_id TEXT NOT NULL,
                scope TEXT NOT NULL DEFAULT 'relationship',
                memory_type TEXT NOT NULL DEFAULT 'episode',
                subject_id TEXT,
                content TEXT NOT NULL,
                summary TEXT,
                embedding vector(384),
                source_turn_ids UUID[] DEFAULT '{}',
                confidence DOUBLE PRECISION DEFAULT 1.0,
                importance DOUBLE PRECISION DEFAULT 1.0,
                status TEXT DEFAULT 'active',
                supersedes_id UUID REFERENCES memory_items(id),
                hit_count INTEGER DEFAULT 0,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                last_used_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'
            );
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_items_character ON memory_items(character_id);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_items_type ON memory_items(memory_type);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_items_active ON memory_items(character_id, status);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_memory_items_embedding ON memory_items USING hnsw (embedding vector_cosine_ops);"
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS memory_consolidation_jobs (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                character_id TEXT NOT NULL,
                status TEXT NOT NULL DEFAULT 'pending',
                turn_ids UUID[] NOT NULL DEFAULT '{}',
                error TEXT,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                updated_at TIMESTAMPTZ DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'
            );
            """
        )

        await _migrate_old_memory_tables(conn)
        await conn.execute("DROP TABLE IF EXISTS relations;")
        await conn.execute("DROP TABLE IF EXISTS entities;")
        await conn.execute("DROP TABLE IF EXISTS conversation_log;")
        await conn.execute("DROP TABLE IF EXISTS episodic_memory;")

        logger.info("PostgreSQL memory schema initialized")


async def _migrate_old_memory_tables(conn: asyncpg.Connection) -> None:
    has_turn_log = await conn.fetchval("SELECT to_regclass('public.conversation_log');")
    if has_turn_log:
        await conn.execute(
            """
            INSERT INTO conversation_turns (
                id,
                session_id,
                user_id,
                character_id,
                user_message,
                assistant_message,
                narrative,
                embedding,
                created_at,
                processed_at,
                metadata
            )
            SELECT
                id,
                0,
                COALESCE(metadata->>'user_id', 'default_user'),
                character_id,
                COALESCE(content, narrative, ''),
                '',
                COALESCE(narrative, content, ''),
                embedding,
                COALESCE(created_at, NOW()),
                CASE WHEN COALESCE(is_processed, false) THEN NOW() ELSE NULL END,
                COALESCE(metadata, '{}'::jsonb)
            FROM conversation_log
            ON CONFLICT (id) DO NOTHING;
            """
        )

    has_long_term = await conn.fetchval("SELECT to_regclass('public.episodic_memory');")
    if has_long_term:
        await conn.execute(
            """
            INSERT INTO memory_items (
                id,
                character_id,
                scope,
                memory_type,
                subject_id,
                content,
                embedding,
                confidence,
                importance,
                status,
                created_at,
                updated_at,
                last_used_at,
                metadata
            )
            SELECT
                id,
                character_id,
                'relationship',
                'episode',
                character_id,
                content,
                embedding,
                1.0,
                1.0,
                COALESCE(status, 'active'),
                COALESCE(created_at, NOW()),
                COALESCE(created_at, NOW()),
                last_hit_at,
                jsonb_build_object('legacy_batch_id', batch_id, 'legacy_hit_count', hit_count)
                    || COALESCE(metadata, '{}'::jsonb)
            FROM episodic_memory
            ON CONFLICT (id) DO NOTHING;
            """
        )
