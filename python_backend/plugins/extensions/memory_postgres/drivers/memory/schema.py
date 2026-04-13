import logging

import asyncpg

logger = logging.getLogger("PostgresDriver.Schema")


async def initialize_schema(pool: asyncpg.Pool) -> None:
    async with pool.acquire() as conn:
        await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS episodic_memory (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                character_id TEXT NOT NULL,
                content TEXT NOT NULL,
                embedding vector(384),
                created_at TIMESTAMPTZ DEFAULT NOW(),
                status TEXT DEFAULT 'active',
                batch_id TEXT,
                hit_count INTEGER DEFAULT 0,
                last_hit_at TIMESTAMPTZ,
                metadata JSONB DEFAULT '{}'
            );
            """
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mem_character ON episodic_memory(character_id);"
        )
        await conn.execute(
            "CREATE INDEX IF NOT EXISTS idx_mem_embedding ON episodic_memory USING hnsw (embedding vector_cosine_ops);"
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS conversation_log (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                character_id TEXT NOT NULL,
                content TEXT,
                narrative TEXT,
                embedding vector(384),
                is_processed BOOLEAN DEFAULT FALSE,
                created_at TIMESTAMPTZ DEFAULT NOW(),
                metadata JSONB DEFAULT '{}'
            );
            """
        )
        await conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN IF NOT EXISTS narrative TEXT;"
        )
        await conn.execute(
            "ALTER TABLE conversation_log ADD COLUMN IF NOT EXISTS is_processed BOOLEAN DEFAULT FALSE;"
        )

        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS entities (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                type TEXT NOT NULL,
                metadata JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )
        await conn.execute(
            """
            CREATE TABLE IF NOT EXISTS relations (
                id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                subject_id TEXT REFERENCES entities(id),
                predicate TEXT NOT NULL,
                object_id TEXT REFERENCES entities(id),
                data JSONB DEFAULT '{}',
                created_at TIMESTAMPTZ DEFAULT NOW()
            );
            """
        )

        logger.info("PostgreSQL schema initialized")
