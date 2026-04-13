"""
[DEPRECATED] This module is scheduled for removal.

Migration Path:
- Use `memory.factory.MemoryDriverFactory` to get drivers directly
- Use `services.container.services.get_memory()` for high-level access
- RAG via `services.chat.pipeline.ChatPipeline`

This file will be removed in a future version.
"""
import asyncio
import warnings
warnings.warn(
    "memory.core.MemoryService is deprecated. Use memory.factory.MemoryDriverFactory instead.",
    DeprecationWarning,
    stacklevel=2
)

import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from memory.vector_store import VectorStore
# from memory.connection import DBConnection # Deprecated
from memory.factory import MemoryDriverFactory, NoOpDriver # Use Factory and shared NoOp
# Concrete drivers loaded dynamically


logger = logging.getLogger("memory.core")


class MemoryService:
    """
    Service for Memory System.
    Delegates to VectorStore and Driver (Postgres, Surreal, etc.).
    """
    
    def __init__(self, character_id: str = "default"):
         self.character_id = character_id
         self.available = True
         self.degraded_reason: Optional[str] = None
         
         try:
             # Use Factory to get driver
             self.driver = MemoryDriverFactory.create_driver()
                     
         except Exception as e:
             logger.critical(f"Failed to load Memory Driver: {e}")
             self.driver = NoOpDriver()
         
         # Components
         self.vector_store = VectorStore(self.driver)
         
         # Injected References
         self.encoder = None
         self.batch_manager = None

    def set_character_id(self, character_id: str):
        """Update active character context at runtime."""
        self.character_id = character_id
        logger.info(f"[MemoryService] Context switched to: {character_id}")

    def set_encoder(self, encoder_fn):
        self.encoder = encoder_fn

    def set_batch_manager(self, manager):
        self.batch_manager = manager

    def set_driver(self, driver):
        self.driver = driver
        self.vector_store.driver = driver

    def set_available(self, value: bool, reason: Optional[str] = None):
        self.available = value
        self.degraded_reason = reason if not value else None

    async def connect(self):
        """Connect to underlying driver."""
        if self.driver:
            await self.driver.connect()

    async def close(self):
        """Close connection."""
        if self.driver:
            await self.driver.close()

    @property
    def db(self):
        """Access underlying DB driver (for legacy compat)."""
        if not self.driver:
            return None
        return getattr(self.driver, "_db", None) or getattr(self.driver, "_pool", None)

    def set_hippocampus(self, hippocampus):
        self._hippocampus = hippocampus
        
    def set_dreaming(self, dreaming):
        self._dreaming = dreaming





    # ================= LOGGING & OPERATIONS =================

    async def log_conversation(self, character_id: str, narrative: str) -> str:
        # db = await DBConnection.get_db() # Deprecated
        try:
            data = {
                "character_id": character_id.lower(),
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


    # Delegate to VectorStore
    async def add_episodic_memory(self, *args, **kwargs):
        return await self.vector_store.add_episodic_memory(*args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self.vector_store.search(*args, **kwargs)

    async def search_fulltext(self, *args, **kwargs):
        return await self.vector_store.search_fulltext(*args, **kwargs)

    async def search_hybrid(self, *args, **kwargs):
        return await self.vector_store.search_hybrid(*args, **kwargs)

    # Legacy Compatibility
    async def add_memory(self, content: str, embedding: List[float], character_id: str, **kwargs) -> str:
        """Legacy wrapper: writes to conversation_log"""
        return await self.log_conversation(character_id, content)



    # ================= UTILITIES =================
    
    async def execute_raw_query(self, sql: str, params: Optional[Dict] = None) -> Any:
        """
        Execute raw SQL query.
        WARNING: Use only for debugging or admin tools.
        """
        if not self.db:
            await self.connect()
        return await self.driver.query(sql, params)

    async def get_stats(self, character_id: str = None) -> Dict:
        """Get memory statistics with parallel query execution."""
        try:
            # [Optimization] Use parameterized query to prevent SQL injection
            if character_id:
                mem_sql = "SELECT count(*) as count FROM episodic_memory WHERE character_id = $1;"
                log_sql = "SELECT count(*) as count FROM conversation_log WHERE character_id = $1;"
                params = {"cid": character_id}
            else:
                mem_sql = "SELECT count(*) as count FROM episodic_memory;"
                log_sql = "SELECT count(*) as count FROM conversation_log;"
                params = {}
            
            # [Optimization] Parallel query execution instead of sequential
            mem_result, log_result = await asyncio.gather(
                self.driver.query(mem_sql, params),
                self.driver.query(log_sql, params),
                return_exceptions=True
            )
            
            def get_cnt(res):
                if isinstance(res, Exception):
                    return 0
                if res and isinstance(res, list) and len(res) > 0:
                    # Handle asyncpg Record format
                    if hasattr(res[0], 'get'):
                        return res[0].get('count', 0)
                    elif isinstance(res[0], dict):
                        return res[0].get('count', 0)
                return 0
                
            return {"entities": get_cnt(mem_result), "conversations": get_cnt(log_result)}
        except Exception:
            return {"entities": 0, "conversations": 0}

    async def get_unprocessed_conversations(self, limit: int = 20, character_id: str = None) -> List[Dict]:
        try:
            if character_id:
                sql = "SELECT * FROM conversation_log WHERE is_processed = false AND character_id = $cid LIMIT $limit;"
                res = await self.driver.query(sql, {"cid": character_id.lower(), "limit": limit})
            else:
                sql = "SELECT * FROM conversation_log WHERE is_processed = false LIMIT $limit;"
                res = await self.driver.query(sql, {"limit": limit})
                
            return self.vector_store._parse_query_result(res)
        except Exception as e:
            logger.error(f"Unprocessed fetch error: {e}")
            return []

    async def mark_conversations_processed(self, conversation_ids: List[str]):
        """Mark multiple conversations as processed in a single batch query."""
        if not conversation_ids:
            return
            
        try:
            await self.driver.query(
                """
                UPDATE conversation_log
                SET is_processed = true
                WHERE id = ANY($ids::uuid[])
                """,
                {"ids": conversation_ids},
            )
            logger.debug(f"Batch marked {len(conversation_ids)} conversations as processed")
        except Exception as e:
            logger.warning(f"Batch mark_processed failed: {e}, falling back to individual updates")
            # Fallback to individual updates if batch fails
            for cid in conversation_ids:
                try:
                    await self.driver.query(f"UPDATE conversation_log SET is_processed = true WHERE id = $1;", {"id": cid})
                except Exception as ex:
                    logger.warning(f"Failed to mark processed {cid}: {ex}")

    async def get_all_conversations(self, character_id: str = None) -> List[Dict]:
        try:
            sql = "SELECT * FROM conversation_log"
            params = {}
            if character_id:
                sql += " WHERE character_id = $cid"
                params["cid"] = character_id
            sql += " ORDER BY created_at DESC LIMIT 1000;"
            res = await self.driver.query(sql, params)
            return self.vector_store._parse_query_result(res)
        except Exception as e:
            logger.error(f"Error fetching conversations: {e}")
            return []
            
    async def get_recent_conversations(self, character_id: str, limit: int = 20) -> List[Dict]:
        sql = "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT $limit;"
        res = await self.driver.query(sql, {"cid": character_id, "limit": limit})
        return self.vector_store._parse_query_result(res)

    async def get_inspiration(self, character_id: str, limit: int = 3) -> List[Dict]:
         try:
             # Random Inspiration
             # Note: Surreal might not support RAND() efficiently on large sets, but fine for now
             # We just fetch recent or random active memories RAG-style without query?
             # Old code fetched result and shuffled python side.
             
             sql = "SELECT * FROM episodic_memory WHERE character_id = $cid AND status = 'active' LIMIT 50;"
             res = await self.driver.query(sql, {"cid": character_id})
             items = self.vector_store._parse_query_result(res)
             import random
             random.shuffle(items)
             return items[:limit]
         except:
             return []
    async def retrieve_context(self, query: str, character_id: str = "default", limit: int = 3) -> str:
        """
        High-Level RAG Retrieval.
        Handles embedding generation and hybrid search internally.
        """
        import asyncio
        try:
            vector = None
            # 1. Internal Embedding Generation (Cached + Non-blocking)
            if self.encoder:
                try:
                    from services.embedding_cache import get_embedding_cache
                    cache = get_embedding_cache()
                    
                    # Check cache first
                    cached = cache.get(query, model_name="memory_encoder")
                    if cached is not None:
                        vector = cached
                    else:
                        # Run sync encoder in thread pool to avoid blocking
                        def _encode():
                            vec = self.encoder(query)
                            if hasattr(vec, "tolist"):
                                vec = vec.tolist()
                            return vec
                        
                        vector = await asyncio.to_thread(_encode)
                        # Cache the result
                        cache.put(query, vector, model_name="memory_encoder")
                        
                except Exception as ex:
                    logger.warning(f"Failed to generate embedding for retrieval: {ex}")

            # 2. Hybrid Search
            results = []
            if vector:
                results = await self.search_hybrid(
                    query=query, 
                    query_vector=vector,  
                    limit=limit, 
                    character_id=character_id
                )
            else:
                # Fallback to full-text only if embedding fails/missing
                logger.warning("Retrieving context without vector (Full-Text fallback)")
                results = await self.search_fulltext(
                    query=query,
                    character_id=character_id,
                    limit=limit
                )

            # 3. Format as String
            if results:
                return "\n".join([r.get('content', '') for r in results])
            
            return ""

        except Exception as e:
            logger.error(f"Context retrieval failed: {e}")
            return ""
