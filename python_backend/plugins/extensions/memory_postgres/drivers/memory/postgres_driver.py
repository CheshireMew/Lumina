import logging
import asyncio
from typing import Dict, Any, Optional, AsyncGenerator
import json
import asyncpg
from pgvector.asyncpg import register_vector
from core.interfaces.driver import BaseMemoryDriver
from core.db.query_builder import QueryBuilder, SecurityException
import re
from app_config import config

logger = logging.getLogger("PostgresDriver")

class PostgresQueryBuilder(QueryBuilder):
    """
    PostgreSQL Implementation of QueryBuilder.
    Constructs SQL with positional placeholders ($1, $2, etc.).
    """

    def sanitize_table(self, table_name: str) -> str:
        # Strict Alphanumeric + Underscore check
        if not re.match(r'^[a-zA-Z0-9_]+$', table_name):
            raise SecurityException(f"Invalid table name: {table_name}")
        return table_name

    def select(self, table: str, where: Optional[Dict[str, Any]] = None, limit: int = 50, order_by: str = "created_at DESC") -> str:
        table = self.sanitize_table(table)
        
        query = f"SELECT * FROM {table}"
        params = {}
        
        # Conditions
        conditions = []
        if where:
            idx = 1
            for key, value in where.items():
                if not re.match(r'^[a-zA-Z0-9_]+$', key):
                    raise SecurityException(f"Invalid column name: {key}")
                
                # Use parameterized query format for asyncpg ($1, $2...)
                # NOTE: The Driver implementation currently expects a dictionary of params
                # BUT asyncpg usually wants a list.
                # However, the Driver.query method in PostgresDriver handles converting dict values to *args?
                # Let's check PostgresDriver.query:
                #    if params: return await conn.fetch(sql, *params.values())
                # So we just need to ensure the order of params.values() matches $1, $2...
                # Dict preservation of insertion order is guaranteed in Python 3.7+
                
                # To be safe and compatible with the QueryBuilder interface which returns (str, dict),
                # we will use named keys in the dict that correspond to what the driver expects.
                # But wait, Postgres uses $1, $2. It doesn't use named parameters like :name.
                # So the query string MUST have $1, $2.
                # And the params dict MUST have keys that when iterated via .values() match 1, 2.
                
                conditions.append(f"{key} = ${idx}")
                params[f"p_{idx}"] = value
                idx += 1
        
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
            
        # Limit & Order
        if not re.match(r'^[a-zA-Z0-9_ ]+(DESC|ASC)?$', order_by, re.IGNORECASE):
             order_by = "created_at DESC"
             
        # Next param index for limit is len(params) + 1
        limit_idx = len(params) + 1
        query += f" ORDER BY {order_by} LIMIT ${limit_idx};"
        params["limit"] = min(limit, 100)
        
        return query, params

    def delete(self, table: str, record_id: str) -> str:
        table = self.sanitize_table(table)
        # ID is always $1
        query = f"DELETE FROM {table} WHERE id = $1;"
        params = {"id": record_id} 
        return query, params
        
    def create(self, table: str, data: Dict[str, Any]) -> str:
        # Not used by admin.py but good for completeness
        # INSERT INTO table (col1, col2) VALUES ($1, $2) RETURNING id;
        table = self.sanitize_table(table)
        columns = []
        placeholders = []
        params = {}
        idx = 1
        for k, v in data.items():
            columns.append(k)
            placeholders.append(f"${idx}")
            params[f"p_{idx}"] = v
            idx += 1
            
        query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id;"
        return query, params

    def update(self, table: str, record_id: str, data: Dict[str, Any]) -> str:
        # UPDATE table SET col1=$1 WHERE id=$2
        table = self.sanitize_table(table)
        sets = []
        params = {}
        idx = 1
        for k, v in data.items():
            sets.append(f"{k} = ${idx}")
            params[f"p_{idx}"] = v
            idx += 1
            
        sets_str = ", ".join(sets)
        query = f"UPDATE {table} SET {sets_str} WHERE id = ${idx};"
        params["id_final"] = record_id
        return query, params


class PostgresDriver(BaseMemoryDriver):
    def __init__(self, id: str = "driver.memory.postgres", name: str = "PostgreSQL Driver", description: str = "Industry Standard Database for Memory & Context"):
        super().__init__(id, name, description)
        self._pool: Optional[asyncpg.Pool] = None
        self._config = config.memory # We will need to update config later
        self._initialized = False
        self._qb = PostgresQueryBuilder()

    def get_query_builder(self) -> 'QueryBuilder':
        return self._qb

    async def load(self):
        """Initialize resources (Called by Plugin Loader)"""
        await self.connect()

    async def connect(self):
        """Establish connection pool"""
        if self._pool:
            return
            
        try:
            # Note: We pull these from the updated config.memory.postgres
            pg_config = self._config.postgres
            user = pg_config.user
            password = pg_config.password
            database = pg_config.database
            host = pg_config.host
            port = pg_config.port

            self._pool = await asyncpg.create_pool(
                user=user,
                password=password,
                database=database,
                host=host,
                port=port,
                min_size=1,
                max_size=10,
                init=self._init_connection
            )
            logger.info(f"✅ Connected to PostgreSQL at {host}:{port}")
            
            # Initialize internal schema
            await self.initialize_schema()
            self._initialized = True
        except Exception as e:
            logger.error(f"❌ PostgreSQL Connection Failed: {e}")
            raise

    async def _init_connection(self, conn):
        """Setup connection types"""
        await register_vector(conn)

    async def close(self):
        if self._pool:
            await self._pool.close()
            self._pool = None

    async def initialize_schema(self):
        """Setup pgvector and core tables"""
        async with self._pool.acquire() as conn:
            # 1. Enable pgvector
            await conn.execute("CREATE EXTENSION IF NOT EXISTS vector;")
            
            # 2. Episodic Memory
            await conn.execute("""
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
            """)
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_character ON episodic_memory(character_id);")
            await conn.execute("CREATE INDEX IF NOT EXISTS idx_mem_embedding ON episodic_memory USING hnsw (embedding vector_cosine_ops);")
            
            # 3. Conversation Log
            await conn.execute("""
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
            """)

            # [Migration] Retroactive fix for existing tables
            try:
                await conn.execute("ALTER TABLE conversation_log ADD COLUMN IF NOT EXISTS narrative TEXT;")
            except Exception as e:
                logger.warning(f"Migration: Failed to add narrative column (likely exists): {e}")
            
            # [Migration] Add is_processed column if missing
            try:
                await conn.execute("ALTER TABLE conversation_log ADD COLUMN IF NOT EXISTS is_processed BOOLEAN DEFAULT FALSE;")
            except Exception as e:
                logger.warning(f"Migration: Failed to add is_processed column: {e}")

            # 4. Knowledge Graph (Entities & Relations)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS entities (
                    id TEXT PRIMARY KEY, -- e.g. "Person:Alice"
                    name TEXT NOT NULL,
                    type TEXT NOT NULL,
                    metadata JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            await conn.execute("""
                CREATE TABLE IF NOT EXISTS relations (
                    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
                    subject_id TEXT REFERENCES entities(id),
                    predicate TEXT NOT NULL,
                    object_id TEXT REFERENCES entities(id),
                    data JSONB DEFAULT '{}',
                    created_at TIMESTAMPTZ DEFAULT NOW()
                );
            """)
            
            logger.info("✨ PostgreSQL Schema Initialized.")

    async def create(self, table: str, data: Dict[str, Any]) -> str:
        """Generic Insert"""
        async with self._pool.acquire() as conn:
            # Handle ID if provided
            columns = []
            placeholders = []
            values = []
            
            idx = 1
            for k, v in data.items():
                columns.append(k)
                placeholders.append(f"${idx}")
                values.append(v)
                idx += 1
            
            query = f"INSERT INTO {table} ({', '.join(columns)}) VALUES ({', '.join(placeholders)}) RETURNING id"
            try:
                result = await conn.fetchval(query, *values)
                return str(result)
            except Exception as e:
                logger.error(f"Postgres Create Error in {table}: {e}")
                raise

    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        """Generic Update (Upsert-like or Merge)"""
        async with self._pool.acquire() as conn:
            sets = []
            values = []
            idx = 1
            for k, v in data.items():
                sets.append(f"{k} = ${idx}")
                values.append(v)
                idx += 1
            
            values.append(id) # ID is the last param
            query = f"UPDATE {table} SET {', '.join(sets)} WHERE id = ${idx}"
            try:
                await conn.execute(query, *values)
                return True
            except Exception as e:
                logger.error(f"Postgres Update Error for {id}: {e}")
                return False

    async def delete(self, table: str, id: str) -> bool:
        async with self._pool.acquire() as conn:
            try:
                await conn.execute(f"DELETE FROM {table} WHERE id = $1", id)
                return True
            except Exception as e:
                logger.error(f"Postgres Delete Error for {id}: {e}")
                return False

    async def query(self, sql: str, params: Optional[Dict] = None) -> Any:
        async with self._pool.acquire() as conn:
            if params:
                # asyncpg uses positional params ($1, $2)
                # If we get dict params, we need to map them or use a helper
                # For now, let's assume raw SQL or simple mapping
                return await conn.fetch(sql, *params.values())
            return await conn.fetch(sql)

    async def mark_memories_hit(self, memory_ids: list):
        async with self._pool.acquire() as conn:
            try:
                # Batch update
                await conn.execute("""
                    UPDATE episodic_memory 
                    SET hit_count = hit_count + 1, 
                        last_hit_at = NOW() 
                    WHERE id = ANY($1::uuid[])
                """, [id for id in memory_ids])
            except Exception as e:
                logger.warning(f"Failed to mark hits: {e}")

    async def search_vector(self, table: str, vector: list, limit: int, threshold: float, filter_criteria: Optional[Dict] = None) -> list:
        async with self._pool.acquire() as conn:
            where_clauses = []
            params = [vector] # $1 is the vector
            
            # Simple filter mapping
            idx = 2
            if filter_criteria:
                for k, v in filter_criteria.items():
                    where_clauses.append(f"{k} = ${idx}")
                    params.append(v)
                    idx += 1
            
            # Cosine similarity is 1 - cosine_distance
            # distance <=> operator gives cosine distance
            # Postgres: 1 - distance > threshold
            where_sql = " AND ".join(where_clauses)
            if where_sql: where_sql = "WHERE " + where_sql + " AND"
            else: where_sql = "WHERE"

            # Threshold check: 1 - (embedding <=> $1) >= threshold
            query = f"""
                SELECT *, (1 - (embedding <=> $1)) as score
                FROM {table}
                {where_sql} (1 - (embedding <=> $1)) >= ${idx}
                ORDER BY score DESC
                LIMIT ${idx + 1}
            """
            params.extend([threshold, limit])
            
            try:
                rows = await conn.fetch(query, *params)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Postgres Vector Search Error: {e}")
                return []

    async def search_fulltext(self, table: str, query: str, limit: int, fields: list, filter_criteria: Optional[Dict] = None) -> list:
        async with self._pool.acquire() as conn:
            where_clauses = []
            params = [query] # $1 is search query
            
            idx = 2
            if filter_criteria:
                for k, v in filter_criteria.items():
                    where_clauses.append(f"{k} = ${idx}")
                    params.append(v)
                    idx += 1
            
            # Simple ILIKE search for now, or fulltext if analyzer set up
            # For Lumina, content is the main field
            search_field = fields[0] if fields else "content"
            
            where_sql = " AND ".join(where_clauses)
            if where_sql: where_sql = "WHERE " + where_sql + " AND"
            else: where_sql = "WHERE"
            
            sql = f"""
                SELECT *, 1.0 as score
                FROM {table}
                {where_sql} {search_field} ILIKE ${idx}
                ORDER BY created_at DESC
                LIMIT ${idx + 1}
            """
            params.extend([f"%{query}%", limit])
            
            try:
                rows = await conn.fetch(sql, *params)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Postgres FullText Search Error: {e}")
                return []

    async def search_hybrid(self, query: str, vector: list, table: str, limit: int, threshold: float, vector_weight: float = 0.5, filter_criteria: Optional[Dict] = None) -> list:
        """
        RRF (Reciprocal Rank Fusion) for PostgreSQL.
        Combines Vector (Cosine) and FullText (ILIKE for now).
        """
        # 1. Vector Search
        # We use a slightly larger limit to ensure we have enough overlap
        vec_results = await self.search_vector(table, vector, limit * 2, threshold, filter_criteria)
        
        # 2. Text Search
        text_results = await self.search_fulltext(table, query, limit * 2, ["content"], filter_criteria)
        
        # 3. RRF Fusion
        scores = {}
        items = {}
        k = 60 # Standard RRF constant
        
        def process_list(lst, weight):
            for rank, item in enumerate(lst):
                item_id = str(item.get('id'))
                if not item_id: continue
                
                if item_id not in scores:
                    scores[item_id] = 0
                    items[item_id] = item
                
                # Formula: weight / (k + rank)
                scores[item_id] += weight / (k + rank + 1)

        process_list(vec_results, vector_weight)
        process_list(text_results, 1.0 - vector_weight)
        
        # Sort and limit
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        results = []
        for item_id in sorted_ids[:limit]:
            item = items[item_id]
            item['hybrid_score'] = scores[item_id]
            results.append(item)
            
        return results

    # --- 馃枼锔?Knowledge Graph ---

    async def relate(self, subject: str, predicate: str, object: str, data: Optional[Dict] = None) -> bool:
        """Create or Update entity relationship"""
        async with self._pool.acquire() as conn:
            try:
                # 1. Ensure entities exist (simplified)
                await conn.execute("INSERT INTO entities (id, name, type) VALUES ($1, $1, 'auto') ON CONFLICT DO NOTHING", subject)
                await conn.execute("INSERT INTO entities (id, name, type) VALUES ($1, $1, 'auto') ON CONFLICT DO NOTHING", object)
                
                # 2. Insert relation
                await conn.execute("""
                    INSERT INTO relations (subject_id, predicate, object_id, data) 
                    VALUES ($1, $2, $3, $4)
                """, subject, predicate, object, json.dumps(data or {}))
                return True
            except Exception as e:
                logger.error(f"Postgres Relate Error: {e}")
                return False

    async def get_neighbors(self, node_id: str, depth: int = 1) -> list:
        """Basic graph traversal"""
        async with self._pool.acquire() as conn:
            try:
                # One level depth simple query
                rows = await conn.fetch("""
                    SELECT r.predicate, e.id, e.name, e.type, e.metadata
                    FROM relations r
                    JOIN entities e ON r.object_id = e.id
                    WHERE r.subject_id = $1
                """, node_id)
                return [dict(row) for row in rows]
            except Exception as e:
                logger.error(f"Postgres Graph Query Error: {e}")
                return []

    # --- 馃搼 Realtime ---

    async def publish(self, channel: str, message: Dict[str, Any]):
        """Broadcast via Postgres NOTIFY"""
        async with self._pool.acquire() as conn:
            try:
                payload = json.dumps(message)
                # IMPORTANT: channel name must be a valid identifier
                await conn.execute(f"SELECT pg_notify($1, $2)", channel, payload)
            except Exception as e:
                logger.error(f"Postgres Publish Error: {e}")

    async def listen(self, channel: str) -> AsyncGenerator[Dict[str, Any], None]:
        """Subscribe via Postgres LISTEN"""
        # asyncpg's listen requires a persistent connection. 
        # Drivers using this should manage their own connection lifecycle.
        # This implementation yields from a queue populated by the listener.
        queue = asyncio.Queue()

        def callback(connection, pid, ch, payload):
            try:
                queue.put_nowait(json.loads(payload))
            except Exception:
                pass

        conn = await self._pool.acquire()
        try:
            await conn.add_listener(channel, callback)
            while True:
                msg = await queue.get()
                yield msg
        finally:
            await conn.remove_listener(channel, callback)
            await self._pool.release(conn)
