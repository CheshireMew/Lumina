import logging
import asyncio
from datetime import datetime
from queue import Queue
from threading import Thread
from typing import List, Dict, Optional, Any
from app_config import config
from memory.connection import DBConnection
from memory.vector_store import VectorStore

logger = logging.getLogger("memory.core")

class SurrealMemory:
    """
    Facade for Memory System.
    Delegates to VectorStore and DBConnection.
    """
    
    def __init__(self, character_id: str = "default"):
         # Note: connection is singleton, but we keep character_id context here
         self.character_id = character_id
         
         # Components
         self.vector_store = VectorStore()
         
         # Background Queue
         self.queue = Queue()
         self.running = True
         self._worker_thread = None
         
         # Injected References
         self._hippocampus = None
         self.encoder = None
         self.batch_manager = None
         
         # Digest State
         self._last_digest_time = None
         self._digest_lock = False
         self._digest_cooldown_seconds = 30

    @property
    def db(self):
        # Helper to access DB directly if needed (AsyncSurreal object)
        # Note: This property access is synchronous but returns the async client instance
        # However, checking connection state usually requires await. 
        # For backward compatibility with code access .db directly (e.g. self.memory.db.query)
        return DBConnection._db 

    async def connect(self):
        """Initialize connection and schema"""
        await DBConnection.connect()
        await self._initialize_schema()
        self._start_worker()
        
    async def close(self):
        self.running = False
        await DBConnection.close()

    async def _initialize_schema(self):
        """Define tables and indexes"""
        try:
            db = await DBConnection.get_db()
            
            # 1. Conversation Log
            await db.query("DEFINE TABLE conversation_log SCHEMALESS;")
            await db.query("DEFINE INDEX log_character ON conversation_log FIELDS character_id;")
            await db.query("DEFINE INDEX log_time ON conversation_log FIELDS created_at;")
            
            # [Free Tier Opt] Vector Index for Logs
            await db.query("""
                DEFINE INDEX log_embedding ON conversation_log FIELDS embedding 
                MTREE DIMENSION 384 DIST COSINE TYPE F32;
            """)
            
            # 2. Episodic Memory
            await db.query("DEFINE TABLE episodic_memory SCHEMALESS;")
            await db.query("DEFINE INDEX mem_character ON episodic_memory FIELDS character_id;")
            await db.query("DEFINE INDEX mem_status ON episodic_memory FIELDS status;")
            await db.query("DEFINE INDEX mem_time ON episodic_memory FIELDS created_at;")
            
            # Vector Index (384 dim)
            await db.query("""
                DEFINE INDEX mem_embedding ON episodic_memory FIELDS embedding 
                MTREE DIMENSION 384 DIST COSINE TYPE F32;
            """)
            
            # FullText Index
            await db.query("DEFINE ANALYZER my_analyzer TOKENIZERS blank, class FILTERS lowercase, snowball(english);")
            await db.query("DEFINE INDEX mem_content_search ON episodic_memory FIELDS content SEARCH ANALYZER my_analyzer BM25;")
            
            logger.info("✅ Schema initialized")
        except Exception as e:
            logger.warning(f"⚠️ Schema initialization warning: {e}")

    # ================= DEPENDENCY INJECTION =================
    
    def set_encoder(self, encoder):
        self.encoder = encoder
    
    def set_hippocampus(self, hippocampus):
        self._hippocampus = hippocampus
        
    def set_dreaming(self, dreaming):
        self._hippocampus = dreaming
        
    def set_batch_manager(self, manager):
        self.batch_manager = manager

    # ================= WORKER & QUEUE =================

    def _start_worker(self):
        if self._worker_thread: return
        
        def worker_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            while self.running:
                try:
                    task = self.queue.get(timeout=1.0)
                    if task: loop.run_until_complete(self._process_task(task))
                except Exception:
                    pass
            loop.close()
            
        self._worker_thread = Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("[SurrealMemory] Worker started")

    async def _process_task(self, task: Dict):
        task_type = task.get("type", "add")
        if task_type == "add":
            await self._add_memory_from_task(task)

    # ================= LOGGING & OPERATIONS =================

    async def log_conversation(self, character_id: str, narrative: str) -> str:
        db = await DBConnection.get_db()
        try:
            data = {
                "character_id": character_id.lower(),
                "narrative": narrative,
                "created_at": datetime.now().isoformat(),
                "is_processed": False
            }
            
            # [Free Tier Opt] Generate embedding for log (Semantic Search Fallback)
            if self.encoder:
                try:
                    # Embed the narrative for search
                    vec = self.encoder(narrative)
                    data["embedding"] = vec
                except Exception as ex:
                    logger.warning(f"Failed to embed log: {ex}")

            results = await db.create("conversation_log", data)
            if not results: raise ValueError("Empty result")
            return self.vector_store._extract_id(results) # reuse helper?
        except Exception as e:
            logger.error(f"Error logging conversation: {e}")
            raise

    # Delegate to VectorStore
    async def add_episodic_memory(self, *args, **kwargs):
        return await self.vector_store.add_episodic_memory(*args, **kwargs)

    async def search(self, *args, **kwargs):
        return await self.vector_store.search(*args, **kwargs)

    async def search_hybrid(self, *args, **kwargs):
        return await self.vector_store.search_hybrid(*args, **kwargs)

    # Legacy Compatibility
    async def add_memory(self, content: str, embedding: List[float], character_id: str, **kwargs) -> str:
        """Legacy wrapper: writes to conversation_log"""
        return await self.log_conversation(character_id, content)

    def add_memory_async(self, task: Dict):
        if "type" not in task: task["type"] = "add"
        self.queue.put(task)

    async def _add_memory_from_task(self, task: Dict):
        user = task.get("user_input", "")
        ai = task.get("ai_response", "")
        content = f"{task.get('user_name','User')}: {user}\n{task.get('char_name','AI')}: {ai}"
        await self.log_conversation(self.character_id, content)

    # ================= UTILITIES =================
    
    async def get_stats(self, character_id: str = None) -> Dict:
        db = await DBConnection.get_db()
        try:
            filter_sql = f"WHERE character_id = '{character_id}'" if character_id else ""
            mem = await db.query(f"SELECT count() FROM episodic_memory {filter_sql} GROUP ALL;")
            log = await db.query(f"SELECT count() FROM conversation_log {filter_sql} GROUP ALL;")
            
            def get_cnt(res):
                if res and isinstance(res, list) and res[0].get('result'):
                     return res[0]['result'][0].get('count', 0)
                return 0
                
            return {"entities": get_cnt(mem), "conversations": get_cnt(log)}
        except Exception:
            return {"entities": 0, "conversations": 0}

    async def get_unprocessed_conversations(self, limit: int = 20, character_id: str = None) -> List[Dict]:
        db = await DBConnection.get_db()
        try:
            if character_id:
                sql = "SELECT * FROM conversation_log WHERE is_processed = false AND character_id = $cid LIMIT $limit;"
                res = await db.query(sql, {"cid": character_id.lower(), "limit": limit})
            else:
                sql = "SELECT * FROM conversation_log WHERE is_processed = false LIMIT $limit;"
                res = await db.query(sql, {"limit": limit})
                
            return self.vector_store._parse_query_result(res)
        except Exception as e:
            logger.error(f"Unprocessed fetch error: {e}")
            return []

    async def mark_conversations_processed(self, conversation_ids: List[str]):
        db = await DBConnection.get_db()
        for cid in conversation_ids:
            try:
                await db.query(f"UPDATE {cid} SET is_processed = true;")
            except: pass

    async def get_all_conversations(self, character_id: str = None) -> List[Dict]:
        db = await DBConnection.get_db()
        try:
            sql = "SELECT * FROM conversation_log"
            params = {}
            if character_id:
                sql += " WHERE character_id = $cid"
                params["cid"] = character_id
            sql += " ORDER BY created_at DESC LIMIT 1000;"
            res = await db.query(sql, params)
            return self.vector_store._parse_query_result(res)
        except Exception:
            return []
            
    async def get_recent_conversations(self, character_id: str, limit: int = 20) -> List[Dict]:
        db = await DBConnection.get_db()
        sql = "SELECT * FROM conversation_log WHERE character_id = $cid ORDER BY created_at DESC LIMIT $limit;"
        res = await db.query(sql, {"cid": character_id, "limit": limit})
        return self.vector_store._parse_query_result(res)

    async def get_inspiration(self, character_id: str, limit: int = 3) -> List[Dict]:
         db = await DBConnection.get_db()
         try:
             # Random Inspiration
             # Note: Surreal might not support RAND() efficiently on large sets, but fine for now
             # We just fetch recent or random active memories RAG-style without query?
             # Old code fetched result and shuffled python side.
             
             sql = "SELECT * FROM episodic_memory WHERE character_id = $cid AND status = 'active' LIMIT 50;"
             res = await db.query(sql, {"cid": character_id})
             items = self.vector_store._parse_query_result(res)
             import random
             random.shuffle(items)
             return items[:limit]
         except:
             return []
