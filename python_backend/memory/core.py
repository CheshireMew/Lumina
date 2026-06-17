import asyncio
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from memory.vector_store import VectorStore
from core.interfaces.driver import BaseMemoryDriver
from services.companion.context import CompanionContext


logger = logging.getLogger("memory.core")


class MemoryService:
    """
    Service for Memory System.
    Delegates to VectorStore and the configured Postgres-backed driver.
    """
    
    def __init__(self, driver: BaseMemoryDriver):
         if driver is None:
             raise ValueError("MemoryService requires an explicit memory driver.")

         self._driver = driver
         
         self.vector_store = VectorStore(self._driver)
         
         self.encoder = None

    def set_encoder(self, encoder_fn):
        self.encoder = encoder_fn

    @property
    def driver(self):
        """Current memory driver, exposed read-only for diagnostics and raw queries."""
        return self._driver

    @property
    def driver_id(self) -> str:
        return getattr(self._driver, "id", "memory")

    def is_driver_active(self, driver_id: str) -> bool:
        return self.driver_id == driver_id

    async def replace_driver(self, driver, *, close_existing: bool = True):
        current = self._driver
        if current is driver:
            return

        if close_existing and current:
            await current.close()

        self._driver = driver
        self.vector_store.replace_driver(driver)

    async def connect(self):
        """Connect to underlying driver."""
        if self._driver:
            await self._driver.connect()

    async def close(self):
        """Close connection."""
        if self._driver:
            await self._driver.close()

    @property
    def db(self):
        """Expose the underlying connection handle for diagnostics and admin tools."""
        if not self._driver:
            return None
        return getattr(self._driver, "_db", None) or getattr(self._driver, "_pool", None)

    # ================= LOGGING & OPERATIONS =================

    def _character_id(self, context: CompanionContext) -> str:
        if not isinstance(context, CompanionContext):
            raise ValueError("MemoryService requires CompanionContext")

        character_id = str(context.character_id or "").strip()
        if not character_id:
            raise ValueError("CompanionContext.character_id must be configured")
        return character_id.lower()

    def _parse_query_result(self, result: Any) -> List[Dict]:
        if not result:
            return []

        rows = result
        if isinstance(result, dict):
            rows = result.get("result") or result.get("data") or [result]

        parsed = []
        for row in rows:
            if isinstance(row, dict):
                parsed.append(dict(row))
            elif hasattr(row, "items"):
                parsed.append(dict(row.items()))
            else:
                try:
                    parsed.append(dict(row))
                except (TypeError, ValueError):
                    logger.warning("Skipping unparseable memory query row: %r", row)
        return parsed

    async def log_conversation(self, context: CompanionContext, narrative: str) -> str:
        try:
            data = {
                "character_id": self._character_id(context),
                "narrative": narrative,
                "created_at": datetime.now(),  # [Fix] asyncpg expects datetime object, not string
                "is_processed": False
            }
            
            # [Free Tier Opt] Generate embedding for log (Semantic Search Fallback)
            if self.encoder:
                try:
                    # Embed the narrative for search
                    vec = self.encoder(narrative)
                    # [Fix] Convert numpy array to list for JSON/CBOR serialization
                    if hasattr(vec, "tolist"):
                        vec = vec.tolist()
                    data["embedding"] = vec
                except Exception as ex:
                    logger.warning(f"Failed to embed log: {ex}")

            results = await self.driver.create("conversation_log", data)
            if not results: raise ValueError("Empty result")
            return str(results) # Driver returns ID string already
        except Exception as e:
            logger.error(f"Error logging conversation: {e}")
            # Do NOT raise, just log error so chat flow continues even if memory fails?
            # Or raise if critical?
            # User saw 500 Error. Raising is consistent.
            raise

    async def search_episodic(
        self,
        query_vector: list[float],
        context: CompanionContext,
        *,
        limit: int = 10,
    ) -> List[Dict]:
        return await self.vector_store.search(
            query_vector,
            self._character_id(context),
            limit=limit,
            target_table="episodic_memory",
        )

    async def _search_episodic_fulltext(
        self,
        *,
        query: str,
        context: CompanionContext,
        limit: int = 10,
    ) -> List[Dict]:
        return await self.vector_store.search_fulltext(
            query=query,
            character_id=self._character_id(context),
            limit=limit,
            target_table="episodic_memory",
        )

    async def search_episodic_hybrid(
        self,
        *,
        query: str,
        query_vector: list[float],
        context: CompanionContext,
        limit: int = 10,
    ) -> List[Dict]:
        return await self.vector_store.search_hybrid(
            query=query,
            query_vector=query_vector,
            character_id=self._character_id(context),
            limit=limit,
            target_table="episodic_memory",
        )

    # ================= UTILITIES =================
    
    async def execute_raw_query(self, sql: str, params: Optional[Dict] = None) -> Any:
        """
        Execute raw SQL query.
        WARNING: Use only for debugging or admin tools.
        """
        if not self.db:
            await self.connect()
        return await self.driver.query(sql, params)

    async def get_stats(self, context: CompanionContext) -> Dict:
        """Get memory statistics for one companion context."""
        character_id = self._character_id(context)
        mem_sql = "SELECT count(*) as count FROM episodic_memory WHERE character_id = $cid;"
        log_sql = "SELECT count(*) as count FROM conversation_log WHERE character_id = $cid;"
        params = {"cid": character_id}

        mem_result, log_result = await asyncio.gather(
            self.driver.query(mem_sql, params),
            self.driver.query(log_sql, params),
        )

        def get_cnt(res):
            if res and isinstance(res, list) and len(res) > 0:
                if hasattr(res[0], 'get'):
                    return res[0].get('count', 0)
                if isinstance(res[0], dict):
                    return res[0].get('count', 0)
            return 0

        return {"entities": get_cnt(mem_result), "conversations": get_cnt(log_result)}

    async def get_unprocessed_conversations(
        self,
        context: CompanionContext,
        limit: int = 20,
    ) -> List[Dict]:
        sql = "SELECT * FROM conversation_log WHERE is_processed = false AND character_id = $cid LIMIT $limit;"
        res = await self.driver.query(
            sql,
            {"cid": self._character_id(context), "limit": limit},
        )
        return self._parse_query_result(res)

    async def mark_conversations_processed(self, conversation_ids: List[str]):
        """Mark multiple conversations as processed in a single batch query."""
        if not conversation_ids:
            return
            
        await self.driver.query(
            """
            UPDATE conversation_log
            SET is_processed = true
            WHERE id = ANY($ids::uuid[])
            """,
            {"ids": conversation_ids},
        )
        logger.debug(f"Batch marked {len(conversation_ids)} conversations as processed")

    async def get_all_conversations(self, context: CompanionContext) -> List[Dict]:
        sql = "SELECT * FROM conversation_log"
        params = {"cid": self._character_id(context)}
        sql += " WHERE character_id = $cid"
        sql += " ORDER BY created_at DESC LIMIT 1000;"
        res = await self.driver.query(sql, params)
        return self._parse_query_result(res)
            
    async def get_recent_conversations(self, context: CompanionContext, limit: int = 20) -> List[Dict]:
        sql = "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT $limit;"
        res = await self.driver.query(sql, {"cid": self._character_id(context), "limit": limit})
        return self._parse_query_result(res)

    async def get_inspiration(self, context: CompanionContext, limit: int = 3) -> List[Dict]:
        # Random Inspiration
        # We just fetch recent or random active memories RAG-style without query?
        # Old code fetched result and shuffled python side.
        sql = "SELECT * FROM episodic_memory WHERE character_id = $cid AND status = 'active' LIMIT 50;"
        res = await self.driver.query(sql, {"cid": self._character_id(context)})
        items = self._parse_query_result(res)
        import random
        random.shuffle(items)
        return items[:limit]

    async def retrieve_context(self, query: str, context: CompanionContext, limit: int = 3) -> str:
        """
        High-Level RAG Retrieval.
        Handles embedding generation and hybrid search internally.
        """
        import asyncio

        vector = None
        if self.encoder:
            try:
                from services.embedding_cache import get_embedding_cache
                cache = get_embedding_cache()

                cached = cache.get(query, model_name="memory_encoder")
                if cached is not None:
                    vector = cached
                else:
                    def _encode():
                        vec = self.encoder(query)
                        if hasattr(vec, "tolist"):
                            vec = vec.tolist()
                        return vec

                    vector = await asyncio.to_thread(_encode)
                    cache.put(query, vector, model_name="memory_encoder")

            except Exception as ex:
                logger.warning(f"Failed to generate embedding for retrieval: {ex}")

        if vector:
            results = await self.search_episodic_hybrid(
                query=query,
                query_vector=vector,
                context=context,
                limit=limit,
            )
        else:
            logger.warning("Retrieving context without vector (Full-Text fallback)")
            results = await self._search_episodic_fulltext(
                query=query,
                context=context,
                limit=limit,
            )

        if results:
            return "\n".join([r.get('content', '') for r in results])

        return ""
