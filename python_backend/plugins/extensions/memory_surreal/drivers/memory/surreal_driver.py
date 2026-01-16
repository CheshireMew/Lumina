import logging
import asyncio
from typing import Dict, Any, Optional, List
from surrealdb import AsyncSurreal
from core.interfaces.driver import BaseMemoryDriver
from app_config import config  # Standard import path

# ... [Keep imports]

logger = logging.getLogger("SurrealDriver")

class SurrealDriver(BaseMemoryDriver):
    def __init__(self, id: str = "surreal-db", name: str = "SurrealDB Driver", description: str = "Official Async SurrealDB Driver"):
        super().__init__(id, name, description)
        self._db: Optional[AsyncSurreal] = None
        self._config = config.memory
        self._initialized = False

    async def load(self):
         # BaseDriver requires load()
         await self.connect()

    async def connect(self, as_admin: bool = False, _retry_after_init: bool = False):
        """
        Connect to SurrealDB with smart auto-initialization.
        First-time: Uses root to create app user, then reconnects as app user.
        """
        if self._db and not as_admin:
            return self._db

        url = self._config.url
        
        # Try app user first (fast path for already-initialized DBs)
        if not as_admin and not _retry_after_init:
            try:
                db = AsyncSurreal(url)
                await asyncio.wait_for(db.connect(), timeout=5.0)
                await db.signin({
                    "username": self._config.app_user,
                    "password": self._config.app_password
                })
                await db.use(self._config.namespace, self._config.database)
                self._db = db
                logger.info(f"鉁?SurrealDriver connected (User: {self._config.app_user})")
                return db
            except Exception as e:
                logger.info(f"ℹ️ App user login validation failed (Expected for first run): {e}")
                logger.info("馃敡 Attempting first-time initialization with root...")
        
        # Root connection (for init or explicit admin request)
        try:
            db = AsyncSurreal(url)
            await asyncio.wait_for(db.connect(), timeout=5.0)
            await db.signin({
                "username": self._config.root_user,
                "password": self._config.root_password
            })
            await db.use(self._config.namespace, self._config.database)
            
            if as_admin:
                return db
            
            # First-time setup: Create app user and schema
            if not self._initialized:
                await self._first_time_init(db)
                self._initialized = True
            
            # Try reconnecting as app user ONCE
            if not _retry_after_init:
                await db.close()
                try:
                    return await self.connect(as_admin=False, _retry_after_init=True)
                except Exception:
                    logger.warning("鈿狅笍 App user still failed after init, using root connection")
            
            # Fallback: just use root connection
            self._db = db
            logger.info(f"鉁?SurrealDriver connected (User: {self._config.root_user}, fallback)")
            return db
            
        except Exception as e:
            logger.error(f"鉂?Root connection failed: {e}")
            raise

    async def _first_time_init(self, admin_db):
        """Create app user and schema (only runs on first connect)"""
        logger.info("馃殌 First-time initialization starting...")
        
        app_user = self._config.app_user
        app_pass = self._config.app_password
        
        # Create app user (IF NOT EXISTS for safety)
        try:
            await admin_db.query(f"""
                DEFINE USER IF NOT EXISTS {app_user} ON DATABASE PASSWORD '{app_pass}' ROLES EDITOR;
            """)
            logger.info(f"馃懁 Created app user: {app_user}")
        except Exception as e:
            logger.warning(f"User creation note: {e}")
        
        # Create tables (SCHEMALESS for flexibility)
        tables = [
            "DEFINE TABLE IF NOT EXISTS conversation_log SCHEMALESS;",
            "DEFINE INDEX IF NOT EXISTS log_character ON conversation_log FIELDS character_id;",
            "DEFINE INDEX IF NOT EXISTS log_time ON conversation_log FIELDS created_at;",
        ]
        for stmt in tables:
            try:
                await admin_db.query(stmt)
            except Exception as e:
                logger.debug(f"Schema note: {e}")
        
        logger.info("鉁?First-time initialization complete!")

    async def close(self):
        if self._db:
            try:
                await self._db.close()
            except Exception as e:
                logger.warning(f"Error closing SurrealDB: {e}")
            finally:
                self._db = None

    async def initialize_schema(self):
        """Define tables, indexes AND Users (Run as Admin)"""
        admin_db = None
        try:
            logger.info("馃洝锔?Initializing Schema & RBAC as Root...")
            # 1. Connect as Root
            admin_db = await self.connect(as_admin=True)
            
            # 2. Define App User (Idempotent)
            # DEFINE USER ... ON DATABASE ...
            app_user = self._config.app_user
            app_pass = self._config.app_password
            
            # Roles: "viewer", "editor" are built-in for SurrealDB 2.0+? 
            # Actually standard SurrealDB 1.x uses permissions. 
            # 2.x uses DEFINE ACCESS ...
            # Let's assume 1.x/2.0 compatible simple user def for now or use RROLES if available.
            # Safe bet: DEFINE USER ... ROLES [OWNER] (too strong?) or custom permissions.
            # Plan said: RROLES ['editor']
            
            await admin_db.query(f"""
                DEFINE USER IF NOT EXISTS {app_user} ON DATABASE PASSWORD '{app_pass}' ROLES EDITOR;
            """)
            logger.info(f"馃懁 App User '{app_user}' ensured.")

            # 3. Tables & Indexes
            await admin_db.query("DEFINE TABLE conversation_log SCHEMALESS;")
            await admin_db.query("DEFINE INDEX log_character ON conversation_log FIELDS character_id;")
            await admin_db.query("DEFINE INDEX log_time ON conversation_log FIELDS created_at;")
            
            # [Free Tier Opt] Vector Index for Logs
            await admin_db.query("""
                DEFINE INDEX log_embedding ON conversation_log FIELDS embedding 
                MTREE DIMENSION 384 DIST COSINE TYPE F32;
            """)
            
            # 2. Episodic Memory
            await admin_db.query("DEFINE TABLE episodic_memory SCHEMALESS;")
            await admin_db.query("DEFINE INDEX mem_character ON episodic_memory FIELDS character_id;")
            await admin_db.query("DEFINE INDEX mem_status ON episodic_memory FIELDS status;")
            await admin_db.query("DEFINE INDEX mem_time ON episodic_memory FIELDS created_at;")
            
            # Vector Index (384 dim)
            await admin_db.query("""
                DEFINE INDEX mem_embedding ON episodic_memory FIELDS embedding 
                MTREE DIMENSION 384 DIST COSINE TYPE F32;
            """)
            
            # FullText Index
            await admin_db.query("DEFINE ANALYZER my_analyzer TOKENIZERS blank, class FILTERS lowercase, snowball(english);")
            await admin_db.query("DEFINE INDEX mem_content_search ON episodic_memory FIELDS content SEARCH ANALYZER my_analyzer BM25;")
            
            logger.info("鉁?SurrealSchema initialized (Admin Mode)")
            
        except Exception as e:
            logger.warning(f"鈿狅笍 Schema initialization warning: {e}")
        finally:
            if admin_db:
                await admin_db.close()

    async def create(self, table: str, data: Dict[str, Any]) -> str:
        await self.connect()
        try:
            results = await self._db.create(table, data)
            return self._extract_id(results)
        except Exception as e:
            logger.error(f"Create error in {table}: {e}")
            raise

    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        await self.connect()
        try:
            # Handle full ID vs partial ID
            target_id = id if ":" in id else f"{table}:{id}"
            await self._db.merge(target_id, data)
            return True
        except Exception as e:
            logger.error(f"Update error for {id}: {e}")
            return False

    async def delete(self, table: str, id: str) -> bool:
        await self.connect()
        try:
            target_id = id if ":" in id else f"{table}:{id}"
            await self._db.delete(target_id)
            return True
        except Exception as e:
            logger.error(f"Delete error for {id}: {e}")
            return False

    async def query(self, sql: str, params: Optional[Dict] = None) -> Any:
        """Execute raw SafeQL query."""
        await self.connect()
        try:
            return await self._db.query(sql, params)
        except Exception as e:
            logger.error(f"Query error: {e}")
            raise

    async def mark_memories_hit(self, memory_ids: List[str]):
        """Increment hit count for memories"""
        await self.connect()
        for mem_id in memory_ids:
            try:
                # Raw query via driver
                target_id = mem_id if ":" in mem_id else f"episodic_memory:{mem_id}"
                await self._db.query(f"""
                    UPDATE {target_id} SET 
                        hit_count = (hit_count ?? 0) + 1,
                        last_hit_at = time::now()
                """)
            except Exception as e:
                logger.warning(f"Failed to mark hit {mem_id}: {e}")

    async def search_vector(self, 
                          table: str, 
                          vector: list, 
                          limit: int, 
                          threshold: float,
                          filter_criteria: Optional[Dict] = None) -> list:
        await self.connect()
        
        where_clause = self._build_where(filter_criteria)
        
        sql = f"""
        SELECT *, vector::similarity::cosine(embedding, $query_vec) AS score 
        FROM {table} 
        WHERE {where_clause}
          AND vector::similarity::cosine(embedding, $query_vec) > $threshold
        ORDER BY score DESC 
        LIMIT $limit;
        """
        
        params = {
            "query_vec": vector,
            "threshold": threshold,
            "limit": limit
        }
        if filter_criteria: params.update(filter_criteria)
        
        res = await self._db.query(sql, params)
        return self._parse_result(res)

    async def search_fulltext(self, 
                            table: str, 
                            query: str, 
                            limit: int,
                            fields: Optional[List[str]] = None,
                            filter_criteria: Optional[Dict] = None) -> list:
        await self.connect()
        
        where_clause = self._build_where(filter_criteria)
        target_field = "content" if table == "episodic_memory" else "narrative"
        if fields and len(fields) > 0: target_field = fields[0] # Simplification
        
        sql = f"""
        SELECT *, 1.0 AS relevance 
        FROM {table}
        WHERE string::lowercase({target_field}) CONTAINS string::lowercase($query)
          AND {where_clause}
        ORDER BY created_at DESC
        LIMIT $limit;
        """
        
        params = {
            "query": query,
            "limit": limit
        }
        if filter_criteria: params.update(filter_criteria)
        
        res = await self._db.query(sql, params)
        return self._parse_result(res)

    async def search_hybrid(self, query: str, vector: list, table: str, limit: int, threshold: float, vector_weight: float = 0.5, filter_criteria: Optional[Dict] = None) -> list:
        # Default RRF implementation (Simplified version of what was in VectorStore)
        # Or here we can implement native if driver supports it. 
        # For now, let's keep it simple: Perform 2 queries and merge. 
        # But wait, logic was in VectorStore to be generic. 
        # Actually, if we want to be optimizing, Surreal should do it.
        # But RRF in Python is fine for now to keep logic consistent.
        # BUT, the Interface says `search_hybrid`.
        # Drivers CAN return None or raise NotImplementedError to let Store handle it? 
        # Or better: Store handles the orchestration if Driver doesn't support "native_hybrid".
        # Let's implement the basic 2-query fetch here so VectorStore just calls this.
        
        # 1. Vector Search
        vec_results = await self.search_vector(table, vector, limit * 2, threshold, filter_criteria)
        
        # 2. Text Search
        text_results = await self.search_fulltext(table, query, limit * 2, None, filter_criteria)
        
        # 3. RRF Fusion (Simplified version)
        scores = {}
        items = {}
        k = 60
        
        def process_list(lst, weight):
            for rank, item in enumerate(lst):
                item_id = str(item.get('id', rank))
                if item_id not in scores:
                    scores[item_id] = 0
                    items[item_id] = item
                scores[item_id] += weight / (k + rank + 1)

        process_list(vec_results, vector_weight)
        process_list(text_results, 1.0 - vector_weight)
        
        sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
        results = []
        for item_id in sorted_ids[:limit]:
            item = items[item_id]
            item['hybrid_score'] = scores[item_id]
            results.append(item)
            
        return results

    # --- Helpers ---

    def _build_where(self, filters: Optional[Dict]) -> str:
        if not filters: return "true"
        clauses = []
        for k, v in filters.items():
            # If value is simple param, use $param
            clauses.append(f"{k} = ${k}")
        return " AND ".join(clauses)

    def _extract_id(self, results) -> str:
        if isinstance(results, list) and results:
            item = results[0]
            if isinstance(item, dict): return item.get('id', '')
        if isinstance(results, dict): return results.get('id', '')
        return str(results)

    def _parse_result(self, res) -> List[Dict]:
        """Robust parser for SurrealDB results"""
        if not res: return []
        if isinstance(res, dict):
            if 'result' in res:
                val = res['result']
                return val if isinstance(val, list) else [val]
            return [res]
        if isinstance(res, list):
            first = res[0]
            if isinstance(first, dict):
                if 'result' in first:
                    val = first['result']
                    return val if val else []
                return res
        return []
