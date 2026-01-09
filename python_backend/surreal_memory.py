import logging
import json
import os
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Any, Tuple
from queue import Queue
from threading import Thread
from surrealdb import Surreal, AsyncSurreal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("surreal_memory")


class SurrealMemory:
    """
    SurrealDB 统一存储适配器
    
    支持:
    - 向量搜索 (HNSW)
    - 全文搜索
    - 对话日志
    - 多角色隔离 (Character ID)
    """
    
    def __init__(self, url: str = "ws://127.0.0.1:8000/rpc", user: str = "root", password: str = "root", 
                 db_namespace: str = "lumina", db_name: str = "memory",
                 character_id: str = "default"):
        self.url = url
        self.user = user
        self.password = password
        self.namespace = db_namespace
        self.database = db_name
        self.character_id = character_id
        self.db: Optional[AsyncSurreal] = None
        
        # Background Queue (for async add)
        self.queue = Queue()
        self.running = True
        self._worker_thread = None
        
        self._hippocampus = None  # Reference injected by main.py
        self._last_digest_time: Optional[datetime] = None
        self._digest_cooldown_seconds: int = 30  # 冷却时间（秒）
        self._digest_lock = False  # 防止并发触发
        
        # Embedding Encoder (Injected)
        self.encoder = None
        
        # BatchManager (Injected) - 用于检索-整合批次管理
        self.batch_manager = None
        


    def set_encoder(self, encoder):
        """Inject embedding encoder for entity resolution."""
        self.encoder = encoder
        logger.info("[SurrealMemory] 🧠 Encoder injected")

    def set_hippocampus(self, hippocampus):
        """注入 Hippocampus 引用，用于自动触发消化"""
        self._hippocampus = hippocampus
        logger.info("[SurrealMemory] 🧠 Hippocampus reference injected")
    
    def set_dreaming(self, dreaming):
        """注入 Dreaming 引用（替代 Hippocampus）"""
        self._hippocampus = dreaming  # 兼容旧代码
        logger.info("[SurrealMemory] 🧠 Dreaming reference injected")
    
    def set_batch_manager(self, manager):
        """注入 BatchManager 用于检索-整合批次管理"""
        self.batch_manager = manager
        logger.info("[SurrealMemory] 📦 BatchManager injected")
    
    async def _trigger_digest_if_ready(self):
        """检查冷却时间，异步触发 Hippocampus 消化（单条处理）"""
        # 1. 检查是否有 Hippocampus 引用
        if not self._hippocampus:
            logger.debug("[SurrealMemory] ⏭️ No Hippocampus reference, skipping digest trigger")
            return
        
        # 2. 检查是否正在处理中（防止并发）
        if self._digest_lock:
            logger.debug("[SurrealMemory] 🔒 Digest already in progress, skipping")
            return
        
        # 3. 检查冷却时间
        now = datetime.now()
        if self._last_digest_time:
            elapsed = (now - self._last_digest_time).total_seconds()
            if elapsed < self._digest_cooldown_seconds:
                remaining = self._digest_cooldown_seconds - elapsed
                logger.debug(f"[SurrealMemory] ⏱️ Cooldown active, {remaining:.1f}s remaining")
                return
        
        # 4. 触发消化
        logger.info("[SurrealMemory] 🔔 Triggering Hippocampus digest...")
        self._digest_lock = True
        self._last_digest_time = now
        
        try:
            # 异步调用 Hippocampus（单条处理）
            await self._hippocampus.process_memories(batch_size=1)
            logger.info("[SurrealMemory] ✅ Hippocampus digest triggered successfully")
        except Exception as e:
            logger.error(f"[SurrealMemory] ❌ Hippocampus digest failed: {e}")
        finally:
            self._digest_lock = False

    async def connect(self):
        """Establish connection to SurrealDB."""
        try:
            self.db = AsyncSurreal(self.url)
            await self.db.connect()
            await self.db.signin({"username": self.user, "password": self.password})
            await self.db.use(self.namespace, self.database)
            logger.info("✅ Connected to SurrealDB")
            
            await self._initialize_schema()
            
            # Start background worker
            self._start_worker()
        except Exception as e:
            logger.error(f"❌ Failed to connect to SurrealDB: {e}")
            raise

    async def _initialize_schema(self):
        """Define tables, indexes for dual-table architecture."""
        if not self.db:
            return

        try:
            # ==================== Dual-Table Architecture ====================
            
            # 1. conversation_log - Raw dialogue (NO embeddings)
            await self.db.query("DEFINE TABLE conversation_log SCHEMALESS;")
            await self.db.query("DEFINE INDEX log_character ON conversation_log FIELDS character_id;")
            await self.db.query("DEFINE INDEX log_time ON conversation_log FIELDS created_at;")
            await self.db.query("DEFINE INDEX log_processed ON conversation_log FIELDS is_processed;")
            
            # 2. episodic_memory - Processed memories (WITH embeddings for RAG)
            await self.db.query("DEFINE TABLE episodic_memory SCHEMALESS;")
            await self.db.query("DEFINE INDEX mem_character ON episodic_memory FIELDS character_id;")
            await self.db.query("DEFINE INDEX mem_status ON episodic_memory FIELDS status;")
            await self.db.query("DEFINE INDEX mem_time ON episodic_memory FIELDS created_at;")
            
            # Vector search index on episodic_memory (384 dim for paraphrase-multilingual-MiniLM-L12-v2)
            await self.db.query("""
                DEFINE INDEX mem_embedding ON episodic_memory FIELDS embedding 
                MTREE DIMENSION 384 DIST COSINE TYPE F32;
            """)
            
            # Full-text search on episodic_memory content
            await self.db.query("DEFINE ANALYZER my_analyzer TOKENIZERS blank, class FILTERS lowercase, snowball(english);")
            await self.db.query("DEFINE INDEX mem_content_search ON episodic_memory FIELDS content SEARCH ANALYZER my_analyzer BM25;")
            
            # 3. Graph Nodes (Unified Entity) - Keep for Knowledge Graph
            await self.db.query("DEFINE TABLE entity SCHEMALESS;")
            await self.db.query("DEFINE INDEX entity_name ON entity FIELDS name;")
            
            logger.info("✅ Schema initialized (Dual-Table: conversation_log + episodic_memory)")
        except Exception as e:
            logger.warning(f"⚠️ Schema initialization warning: {e}")

    def _start_worker(self):
        """Start background worker thread for async operations."""
        if self._worker_thread is not None:
            return
            
        def worker_loop():
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            
            while self.running:
                try:
                    task = self.queue.get(timeout=1.0)
                    if task is None:
                        continue
                    
                    loop.run_until_complete(self._process_task(task))
                except Exception:
                    pass  # Timeout or error, continue
            
            loop.close()
        
        self._worker_thread = Thread(target=worker_loop, daemon=True)
        self._worker_thread.start()
        logger.info("[SurrealMemory] Background worker started")

    async def _process_task(self, task: Dict):
        """Process a queued task."""
        task_type = task.get("type", "add")
        
        if task_type == "add":
            await self._add_memory_from_task(task)
        elif task_type == "conversation":
            await self._log_conversation(task)

    # ==================== Core Memory Operations ====================
    
    async def log_conversation(self, character_id: str, narrative: str) -> str:
        """
        Log raw dialogue to conversation_log table (NO embedding).
        Called by routers/memory.py after each conversation turn.
        """
        if not self.db:
            await self.connect()

        try:
            data = {
                "character_id": character_id.lower(),
                "narrative": narrative,
                "created_at": datetime.now().isoformat(),
                "is_processed": False
            }
            
            results = await self.db.create("conversation_log", data)
            
            if not results:
                raise ValueError("Create returned empty result")

            result_item = results[0] if isinstance(results, list) else results
            record_id = result_item.get('id', str(results))

            logger.debug(f"📝 Conversation logged: {record_id}")
            return str(record_id)

        except Exception as e:
            logger.error(f"❌ Error logging conversation: {e}")
            raise

    async def add_episodic_memory(self, 
                                  character_id: str, 
                                  content: str, 
                                  embedding: List[float],
                                  status: str = "active") -> str:
        """
        Add processed memory to episodic_memory table (WITH embedding).
        Called by Dreaming Extractor/Consolidator.
        """
        if not self.db:
            await self.connect()

        try:
            data = {
                "character_id": character_id.lower(),
                "content": content,
                "embedding": embedding,
                "created_at": datetime.now().isoformat(),
                "status": status,
                # 新增字段（为批次管理准备）
                "batch_id": None,
                "hit_count": 0,
                "last_hit_at": None
            }
            
            logger.debug(f"[add_episodic_memory] Creating record with data keys: {data.keys()}")
            results = await self.db.create("episodic_memory", data)
            logger.debug(f"[add_episodic_memory] Raw result type: {type(results)}, value: {str(results)[:200]}")
            
            if not results:
                raise ValueError("Create returned empty result")

            # 解析不同的 SurrealDB 返回格式
            record_id = None
            
            # 格式 1: 直接是 RecordID 对象
            if hasattr(results, 'id'):
                record_id = str(results.id) if hasattr(results.id, '__str__') else str(results)
            # 格式 2: 包含 'id' 键的字典
            elif isinstance(results, dict) and 'id' in results:
                record_id = str(results['id'])
            # 格式 3: 列表格式
            elif isinstance(results, list) and len(results) > 0:
                first = results[0]
                if hasattr(first, 'id'):
                    record_id = str(first.id)
                elif isinstance(first, dict) and 'id' in first:
                    record_id = str(first['id'])
                else:
                    record_id = str(first)
            else:
                record_id = str(results)

            logger.info(f"🧠 Episodic memory added: {record_id}")
            return record_id

        except Exception as e:
            logger.error(f"❌ Error adding episodic memory: {e}")
            import traceback
            traceback.print_exc()
            raise

    # ==================== Legacy Compatibility ====================
    
    async def add_memory(self, 
                        content: str, 
                        embedding: List[float], 
                        character_id: str, 
                        user_id: str = "user_default",
                        importance: int = 1,
                        emotion: Optional[str] = None,
                        channel: str = "character") -> str:
        """
        DEPRECATED: Use log_conversation for raw logs, add_episodic_memory for processed.
        Kept for backward compatibility - now writes to conversation_log.
        """
        if not self.db:
            await self.connect()

        try:
            # For backward compatibility, write to conversation_log
            data = {
                "character_id": character_id.lower(),
                "narrative": content,
                "created_at": datetime.now().isoformat(),
                "is_processed": False
            }
            
            results = await self.db.create("conversation_log", data)
            
            if not results:
                raise ValueError("Create returned empty result")

            result_item = results[0] if isinstance(results, list) else results
            record_id = result_item.get('id', str(results))

            logger.info(f"💾 Conversation stored (legacy): {record_id}")
            return str(record_id)

        except Exception as e:
            logger.error(f"❌ Error adding memory: {e}")
            raise

    def add_memory_async(self, task: Dict):
        """Fire-and-forget: Add task to queue (LiteMemory compatible interface)."""
        if "type" not in task:
            task["type"] = "add"
        if "timestamp" not in task:
            task["timestamp"] = datetime.now().isoformat()
        
        self.queue.put(task)
        logger.info(f"[SurrealMemory] Task queued. Queue Size: {self.queue.qsize()}")

    async def _add_memory_from_task(self, task: Dict):
        """Process add task from queue."""
        # Extract content from LiteMemory-style task
        user_input = task.get("user_input", "")
        ai_response = task.get("ai_response", "")
        user_name = task.get("user_name", "User")
        char_name = task.get("char_name", "AI")
        
        content = f"{user_name}: {user_input}\n{char_name}: {ai_response}"
        
        # Generate embedding (requires external encoder)
        # This is a placeholder - actual embedding should be provided
        embedding = task.get("embedding", [0.0] * 384)
        
        await self.add_memory(
            content=content,
            embedding=embedding,
            character_id=self.character_id,
            importance=task.get("importance", 1),
            channel="dialogue"
        )

    # (Removed: Old log_conversation - now handled by the simplified version above)

    # ==================== Graph Operations (New Brain) ====================




    def _sanitize_id(self, raw_id: str) -> str:
        """Helper to sanitize IDs for SurrealDB (handles spaces, symbols, chinese)."""
        # SurrealDB supports complex IDs using ⟨...⟩ brackets.
        return f"⟨{raw_id}⟩"

    async def _resolve_entity(self, raw_name: str) -> Tuple[str, Optional[List[float]]]:
        """
        Resolve entity name to ID using Aliases + Vector De-duplication.
        Returns: (entity_id, embedding_vector)
        """
        raw_name = raw_name.strip()
        
        # 0. Alias Check (Manual Override)
        if hasattr(self, 'aliases') and raw_name in self.aliases:
            resolved_name = self.aliases[raw_name]
            # logger.info(f"🔗 Entity Alias: '{raw_name}' -> '{resolved_name}'")
            sanitized = self._sanitize_id(resolved_name)
            # If alias hit, we assume it exists or will be created with this canonical ID
            return f"entity:{sanitized}", None

        # 0.5 Auto-Case Insensitive Check (Strict DB Match)
        try:
            # Check if an entity with this name (ignoring case) already exists
            ci_query = "SELECT id FROM entity WHERE string::lowercase(name) = string::lowercase($name) LIMIT 1;"
            # surrealdb query returns list of results
            ci_res = await self.db.query(ci_query, {"name": raw_name})
            
            if ci_res and isinstance(ci_res, list) and ci_res[0].get('result'):
                # Found an existing entity with same name (diff case)
                matched_id = ci_res[0]['result'][0]['id']
                # logger.debug(f"🔗 Case-Insensitive Match: '{raw_name}' -> '{matched_id}'")
                return matched_id, None
        except Exception as e:
            logger.warning(f"[SurrealMemory] Case-insensitive check failed: {e}")

        sanitized = self._sanitize_id(raw_name)
        default_id = f"entity:{sanitized}"
        
        if not self.encoder:
            return default_id, None
            
        try:
            # 1. Generate Embedding
            # encoder.encode returns ndarray
            emb_vector = self.encoder.encode([raw_name])[0].tolist()
            
            # 2. Query for semantic match
            query = """
            SELECT id, name, vector::similarity::cosine(embedding, $emb) AS score 
            FROM entity 
            WHERE vector::similarity::cosine(embedding, $emb) > 0.92 
            ORDER BY score DESC 
            LIMIT 1;
            """
            res = await self.db.query(query, {"emb": emb_vector})
            
            if res and isinstance(res, list) and res[0].get('result'):
                # Found a semantic duplicate
                match = res[0]['result'][0]
                matched_id = match['id']
                score = match['score']
                # Only if ID is different (to avoid logging self-match if name exactly same)
                if matched_id != default_id:
                    logger.info(f"🔗 Entity Resolution: '{raw_name}' -> '{match['name']}' (Score: {score:.3f})")
                return matched_id, None # No need to re-save embedding for existing
            
            return default_id, emb_vector
            
        except Exception as e:
            logger.warning(f"Entity Resolution error: {e}")
            return default_id, None

    async def add_knowledge_graph(self, knowledge_list: List[Dict], observer_id: str = "default"):
        """
        Store Level 1 Facts (Knowledge Graph).
        """
        if not self.db:
            await self.connect()

        # Group operations for efficiency? doing one by one for safety first.
        
        # Current time for metadata
        current_time = datetime.now().isoformat()
        char_id = f"character:{self._sanitize_id(observer_id)}"

        for item in knowledge_list:
            try:
                # Expecting: subject, relation, object
                # relation should be uppercase standard (e.g. LIKES)
                subj_raw = item.get("subject")
                rel = item.get("relation", "").upper() # e.g. LIKES
                obj_raw = item.get("object")
                weight = item.get("weight", 0.5) # Default weight

                if not (subj_raw and rel and obj_raw):
                    continue

                # Ensure Table Permissions
                await self.db.query(f"DEFINE TABLE {rel} SCHEMALESS PERMISSIONS FULL;")

                # 1. Resolve & Create Entities (Phase 1.1)
                subj_id, subj_emb = await self._resolve_entity(subj_raw)
                obj_id, obj_emb = await self._resolve_entity(obj_raw)
                
                # Upsert Subject
                subj_set = "name=$name, type='general', last_updated=time::now()"
                subj_params = {"name": subj_raw}
                if subj_emb:
                    subj_set += ", embedding=$emb"
                    subj_params["emb"] = subj_emb
                await self.db.query(f"UPSERT {subj_id} SET {subj_set};", subj_params)

                # Upsert Object
                obj_set = "name=$name, type='general', last_updated=time::now()"
                obj_params = {"name": obj_raw}
                if obj_emb:
                    obj_set += ", embedding=$emb"
                    obj_params["emb"] = obj_emb
                await self.db.query(f"UPSERT {obj_id} SET {obj_set};", obj_params)
                
                # 2. Edge Logic (Phase 1.2: Reinforcement)
                # Check if edge exists
                check_query = f"SELECT id, count, base_strength FROM {rel} WHERE in={subj_id} AND out={obj_id} LIMIT 1;"
                res = await self.db.query(check_query)
                
                target_edge_id = None
                
                # SDK query() returns unwrapped data: [{'id': ...}] directly
                if res and isinstance(res, list) and res[0].get('result'):
                    target_edge_id = res[0]['result'][0]['id']
                    # Edge exists, reinforce it (Muscle Model)
                    update_edge_query = f"""
                    UPDATE {target_edge_id} SET 
                        last_accessed = time::now(),
                        last_mentioned = time::now(),
                        count = (count OR 1) + 1,
                        base_strength = math::min(1.0, (base_strength OR 0.8) + 0.05)
                    ;"""
                    await self.db.query(update_edge_query)
                else:
                    
                    # Generate embedding for Edge Context if available
                    context_text = item.get("context", "")
                    edge_emb = None
                    if context_text and self.encoder:
                        try:
                            edge_emb = self.encoder.encode([context_text])[0].tolist()
                        except Exception as emb_err:
                            logger.warning(f"Failed to embed edge context: {emb_err}")

                    # Create New Relation Edge
                    create_edge_query = f"""
                    RELATE {subj_id}->{rel}->{obj_id} CONTENT {{
                        created_at: time::now(),
                        last_accessed: time::now(),
                        last_mentioned: time::now(),
                        weight: $weight,
                        base_strength: 0.8,
                        count: 1,
                        context: $context,
                        embedding: $emb,
                        source: 'dialogue'
                    }};
                    """
                    res = await self.db.query(create_edge_query, {
                        "weight": weight,
                        "context": context_text,
                        "emb": edge_emb
                    })
                    
                    if res and isinstance(res, list):
                        # Case A: Wrapped (Standard for some queries)
                        if isinstance(res[0], dict) and 'result' in res[0] and res[0]['result']:
                             target_edge_id = res[0]['result'][0]['id']
                        # Case B: Unwrapped (Direct list of records, typical for RELATE/CREATE)
                        elif isinstance(res[0], dict) and 'id' in res[0]:
                             target_edge_id = res[0]['id']
                        else:
                             # Could be empty list if failure
                             logger.warning(f"[SurrealMemory] ⚠️ RELATE returned empty/unknown format: {res}")
                    else:
                        logger.warning(f"[SurrealMemory] ⚠️ RELATE returned nothing: {res}")

                # 4. Link Character to Fact
                if target_edge_id:
                     obs_query = f"""
                     RELATE {char_id}->observes->{target_edge_id} SET
                        last_observed = $time
                     """
                     await self.db.query(obs_query, {"time": current_time})
            
            except Exception as e:
                logger.error(f"❌ Graph update failed: {e}")

                if not (subj and rel and obj):
                    continue

                # Ensure Table Permissions (Fix for implicit tables having NO permissions)
                # We do this for every unique relation encountered to be safe.
                await self.db.query(f"DEFINE TABLE {rel} SCHEMALESS PERMISSIONS FULL;")

                # 1. Create/Update Nodes (Entities)
                # Strategy: Upsert based on name.
                # ID format: entity:Name
                subj_id = f"entity:{self._sanitize_id(subj)}"
                obj_id = f"entity:{self._sanitize_id(obj)}"
                
                # Upsert Subject - 使用 UPSERT 确保记录被创建
                await self.db.query(f"UPSERT {subj_id} SET name=$name, type='general';", {"name": subj})
                # Upsert Object
                await self.db.query(f"UPSERT {obj_id} SET name=$name, type='general';", {"name": obj})
                
                # Check if edge exists
                check_query = f"SELECT id FROM {rel} WHERE in={subj_id} AND out={obj_id} LIMIT 1;"
                res = await self.db.query(check_query)
                
                target_edge_id = None
                
                # SDK query() returns unwrapped data: [{'id': ...}] directly
                if res:
                    target_edge_id = res[0]['id']
                    # Edge exists, reinforce it
                    update_edge_query = f"UPDATE {target_edge_id} SET last_accessed = time::now();"
                    await self.db.query(update_edge_query)
                else:
                    # Create New Relation Edge with ALL fields
                    create_edge_query = f"""
                    RELATE {subj_id}->{rel}->{obj_id} CONTENT {{
                        created_at: time::now(),
                        last_accessed: time::now(),
                        weight: $weight,
                        context: $context,
                        emotion: $emotion,
                        potential_reason: $potential_reason,
                        source: 'dialogue'
                    }};
                    """
                    res = await self.db.query(create_edge_query, {
                        "weight": weight,
                        "context": item.get("context", ""),
                        "emotion": item.get("emotion", ""),
                        "potential_reason": item.get("potential_reason", "")
                    })
                    
                    # SDK returns: [{'id': ..., 'in': ..., 'out': ...}]
                    if res:
                        target_edge_id = res[0]['id']
                    else:
                        logger.warning(f"⚠️ RELATE returned empty: {res}")

                # 4. Link Character to Fact (The 'observes' edge)
                # character -> observes -> (edge)
                if target_edge_id:
                     # Check if observation exists to avoid duplicates (optional, but good for counters)
                     # For now, just simplistic RELATE which handles distinctness if unique index exists? 
                     # SurrealDB RELATE is usually creating new edges. 
                     # We want: If not exists, relate.
                     # Let's just do RELATE. If we want unique, we define index on observer+edge.
                     
                     obs_query = f"""
                     RELATE {char_id}->observes->{target_edge_id} SET
                        last_observed = $time
                     """
                     await self.db.query(obs_query, {"time": current_time})
            
            except Exception as e:
                logger.error(f"❌ Graph update failed: {e}")
                # Don't raise, just log, to prevent crashing the cycle

        logger.info(f"🧠 Processed {len(knowledge_list)} knowledge items for {observer_id}.")
            
    async def add_insights(self, insights: List[Dict], evidence_chain: List[Dict], observer_id: str = "default"):
        """
        Store Level 2 Insights (Reflection) and link them to Level 1 Facts (Evidence).
        """
        if not self.db:
            await self.connect()

        try:
            char_id = f"character:{self._sanitize_id(observer_id)}"
            
            # 1. Create Insight Nodes
            for ins in insights:
                label = ins.get("label")
                if not label: continue
                
                # Insight ID: insight:Artistic_Soul (Safe ID)
                ins_id = f"insight:{self._sanitize_id(label)}"
                
                # Update/Upsert Insight
                update_query = f"""
                UPDATE {ins_id} SET
                    label = $label,
                    description = $desc,
                    confidence = $conf,
                    weight = $weight,
                    type = 'abstract_concept',
                    created_at = time::now()
                ;
                """
                await self.db.query(update_query, {
                    "label": label,
                    "desc": ins.get("description", ""),
                    "conf": ins.get("confidence", 0.5),
                    "weight": ins.get("weight", 0.5)
                })
                
                # Link Agent -> Observes -> Insight
                # The agent "realizes" this insight
                await self.db.query(f"RELATE {char_id}->observes->{ins_id} SET last_observed = time::now();")

            # 2. Link Evidence (Derived From)
            # Insight -> DERIVED_FROM -> Fact Edge (e.g. likes:123)
            for ev in evidence_chain:
                ins_label = ev.get("insight_label")
                subj_name = ev.get("fact_subject")
                rel_type = ev.get("fact_relation", "").upper()
                obj_name = ev.get("fact_object")
                
                if not (ins_label and subj_name and rel_type and obj_name):
                    continue
                    
                ins_id = f"insight:{self._sanitize_id(ins_label)}"
                subj_id = f"entity:{self._sanitize_id(subj_name)}"
                obj_id = f"entity:{self._sanitize_id(obj_name)}"
                
                # Find the Fact Edge ID
                find_query = f"SELECT id FROM {rel_type} WHERE in={subj_id} AND out={obj_id} LIMIT 1;"
                result = await self.db.query(find_query)
                
                # SDK returns: [{'id': ...}] directly
                if result:
                    edge_id = result[0]['id']
                    # Create Link: Insight -> DERIVED_FROM -> Edge
                    relate_query = f"RELATE {ins_id}->derived_from->{edge_id};"
                    await self.db.query(relate_query)
                else:
                    logger.warning(f"⚠️ Evidence edge not found: {subj_name} -[{rel_type}]-> {obj_name}")
            
            logger.info(f"💡 Processed {len(insights)} insights and linked evidence.")

        except Exception as e:
            logger.error(f"❌ Insight update failed: {e}")

    async def get_unprocessed_conversations(self, limit: int = 20, character_id: Optional[str] = None) -> List[Dict]:
        """Fetch conversations that haven't been digested by Hippocampus yet.
        
        Args:
            limit: Maximum number of conversations to return
            character_id: If provided, only return conversations for this character (normalized to lowercase)
        """
        if not self.db:
            await self.connect()
        
        try:
            # ⚡ Build query with optional character_id filter for multi-character isolation
            if character_id:
                normalized_id = character_id.lower()
                query = """
                SELECT * FROM conversation 
                WHERE (is_processed = false OR is_processed IS NONE)
                AND character_id = $character_id
                ORDER BY created_at ASC
                LIMIT $limit;
                """
                result = await self.db.query(query, {"limit": limit, "character_id": normalized_id})
            else:
                # Legacy: No filter (backwards compatible but NOT recommended)
                query = """
                SELECT * FROM conversation 
                WHERE is_processed = false OR is_processed IS NONE
                ORDER BY created_at ASC
                LIMIT $limit;
                """
                result = await self.db.query(query, {"limit": limit})
            
            if result and isinstance(result, list):
                # Try standard format
                if 'result' in result[0]:
                    return result[0]['result']
                # Try direct list format (sometimes happens?)
                return result
            return []
        except Exception as e:
            logger.error(f"Failed to fetch unprocessed conversations: {e}")
            return []

    async def mark_conversations_processed(self, conversation_ids: List[str]):
        """Mark conversations as processed so they aren't read again."""
        if not self.db or not conversation_ids:
            return
            
        try:
            ids_str = ", ".join([f"{cid}" for cid in conversation_ids]) # Assuming IDs are clean record IDs
            # If IDs are just 'conversation:xxxxx', this works. If raw strings, might need formatting.
            # Ideally conversation_ids are full Record IDs provided by SurrealDB (e.g., conversation:123)
            
            # Using a loop for safety or a WHERE IN clause
            # SurrealDB specific: UPDATE conversation:xyz SET is_processed = true;
            for cid in conversation_ids:
                await self.db.query(f"UPDATE {cid} SET is_processed = true;")
                
        except Exception as e:
            logger.error(f"Failed to mark conversations processed: {e}")

    def _parse_query_result(self, res) -> List[Dict]:
        """
        Helper to robustly parse SurrealDB query results.
        Handles:
        1. Direct list of dicts: [{'id':...}, {'id':...}] (New SDK Select)
        2. Wrapped result: [{'result': [{'id':...}], 'status': 'OK'}] (Old Parser)
        3. Single dict: {'tables': ...} (New SDK Info)
        4. Wrapped dict: {'result': {'tables': ...}} (Old Parser Info)
        """
        if not res: return []
        
        # 1. Handle Single Dict (e.g. INFO response in new SDK)
        if isinstance(res, dict):
            # If wrapped
            if 'result' in res:
                val = res['result']
                return val if isinstance(val, list) else [val]
            return [res]
            
        # 2. Handle List (Standard Select)
        if isinstance(res, list):
            # Check first item structure
            if len(res) == 0: return []
            first = res[0]
            if isinstance(first, dict):
                # If wrapped in 'result'
                if 'result' in first:
                    val = first['result']
                    return val if isinstance(val, list) else [val] # might be list of lists if multiple queries?
                # Else assume it's a direct record
                return res
            return []
            
        return []

    async def get_random_inspiration(self, character_id: str = "hiyori", limit: int = 3) -> List[Dict]:
        """
        Fetches random facts from knowledge graph edges for proactive conversation inspiration.
        Returns a list of dicts with context, weight, emotion, relation, subject, object.
        """
        if not self.db:
            await self.connect()
        
        try:
            # Get all edge tables (relation types) for this character
            info = await self.db.query("INFO FOR DB;")
            edge_tables = []
            known_non_edge = ["conversation", "entity", "character", "user", "user_entity", "memory_embeddings", "migrations"]
            
            # Use robust parsing for INFO finding too
            info_res = self._parse_query_result(info)
            if info_res and isinstance(info_res, list) and len(info_res) > 0:
                # INFO returns a dict with 'tables' key usually
                # If parsed correctly, info_res[0] might be the dict containing tables
                # Wait, INFO FOR DB returns { tables: {...}, ... }
                # Let's handle generic structure safely
                data = info_res[0] if isinstance(info_res[0], dict) else {}
                tables_map = data.get('tables', {})
                for tbl in tables_map.keys():
                    if tbl not in known_non_edge and not tbl.startswith("observes"):
                        edge_tables.append(tbl)
            
            if not edge_tables:
                logger.info("[Inspiration] No edge tables found for inspiration")
                return []
            
            # Query random edges from knowledge graph
            # Strategy: 
            # 1. Try via observes relation (character->observes->fact)
            # 2. Fallback to direct edge query if observes is empty
            results = []
            use_direct_fallback = False
            
            for tbl in edge_tables[:5]:  # Limit to 5 tables to avoid too many queries
                try:
                    # ⚡ First try: Use subquery via observes relation
                    query = f"""
                        SELECT * FROM {tbl} 
                        WHERE id IN (SELECT VALUE out FROM observes WHERE in = character:{self._sanitize_id(character_id)})
                        ORDER BY rand() 
                        LIMIT {limit};
                    """
                    res = await self.db.query(query)
                    edges = self._parse_query_result(res)
                    
                    # If observes returns nothing, mark for fallback
                    if not edges and not use_direct_fallback:
                        use_direct_fallback = True
                    
                    for edge in edges:
                        if not isinstance(edge, dict):
                            continue
                            
                        # Extract subject and object from in/out
                        subj = str(edge.get('in', '')).replace('entity:', '')
                        obj = str(edge.get('out', '')).replace('entity:', '')
                        
                        results.append({
                            "relation": tbl.upper(),
                            "subject": subj,
                            "object": obj,
                            "context": edge.get('context', ''),
                            "weight": edge.get('weight', 0.5),
                            "emotion": edge.get('emotion', ''),
                            "potential_reason": edge.get('potential_reason', ''),
                            "created_at": str(edge.get('created_at', ''))
                        })
                        
                except Exception as e:
                    logger.warning(f"[Inspiration] Failed to query {tbl}: {e}")
                    continue
            
            # ⚡ Fallback: If observes returned nothing, query edges directly
            if not results and use_direct_fallback:
                logger.info("[Inspiration] observes returned 0 results, trying direct edge query")
                for tbl in edge_tables[:5]:
                    try:
                        # Direct query: Get random edges from table
                        query = f"""
                            SELECT * FROM {tbl} 
                            ORDER BY rand() 
                            LIMIT {limit};
                        """
                        res = await self.db.query(query)
                        edges = self._parse_query_result(res)
                        
                        for edge in edges:
                            if not isinstance(edge, dict):
                                continue
                            
                            subj = str(edge.get('in', '')).replace('entity:', '')
                            obj = str(edge.get('out', '')).replace('entity:', '')
                            
                            results.append({
                                "relation": tbl.upper(),
                                "subject": subj,
                                "object": obj,
                                "context": edge.get('context', ''),
                                "weight": edge.get('weight', 0.5),
                                "emotion": edge.get('emotion', ''),
                                "potential_reason": edge.get('potential_reason', ''),
                                "created_at": str(edge.get('created_at', ''))
                            })
                    except Exception as e:
                        logger.warning(f"[Inspiration] Direct query {tbl} failed: {e}")
                        continue

            
            # Shuffle and limit
            import random
            random.shuffle(results)
            final_results = results[:limit]
            
            logger.info(f"[Inspiration] Fetched {len(final_results)} random facts from SurrealDB")
            return final_results
            
        except Exception as e:
            logger.error(f"[Inspiration] Error: {e}")
            return []

    async def merge_entity_duplicates(self) -> Tuple[Dict[str, int], List[str]]:
        """
        手动触发实体合并（基于 entity_aliases.json）。
        返回: (metrics, logs)
        """
        if not self.db: await self.connect()
        
        metrics = {"merged_aliases": 0}
        merge_logs = []
        
        def log(msg):
            logger.info(msg)
            merge_logs.append(msg)
            
        log("[Merge] Starting manual entity merge...")
        
        # Reload aliases to ensure fresh config
        self._load_aliases()
        if not self.aliases:
            log("[Merge] No aliases defined in config.")
            return metrics, merge_logs
        
        # Get all tables once
        all_tables = []
        try:
            info = await self.db.query("INFO FOR DB;")
            # SurrealDB response parsing can be tricky
            # info structure: [{'result': {'tables': {...}}, status:'OK'}]
            if info and isinstance(info, list):
                # Try standard format
                if info and 'result' in info[0]:
                    tables_map = info[0]['result'].get('tables', {})
                else: # Try direct list format (sometimes happens?)
                    tables_map = info[0].get('tables', {})
                all_tables = list(tables_map.keys())
            
        except Exception as e:
            log(f"[Merge] Failed to fetch DB info: {e}")
            
        log(f"[Merge] Tables to scan: {len(all_tables)}")

        for alias, canonical in self.aliases.items():
            try:
                # Sanitize IDs
                alias_id = f"entity:{self._sanitize_id(alias)}"
                canonical_id = f"entity:{self._sanitize_id(canonical)}"
                
                if alias_id == canonical_id: continue
                if alias_id == canonical_id: continue
                
                log(f"[Merge] Processing match: '{alias}' -> '{canonical}'")
                
                # Helper to format ID for SQL safely
                def safe_id(id_val):
                    # If it's a RecordID object (has table_name/record_id)
                    if hasattr(id_val, 'table_name') and hasattr(id_val, 'record_id'):
                        return f"{id_val.table_name}:⟨{id_val.record_id}⟩"
                    
                    s = str(id_val)
                    if ":" in s:
                        parts = s.split(":", 1)
                        # Check if already bracketed
                        if parts[1].startswith("⟨") and parts[1].endswith("⟩"):
                            return s
                        return f"{parts[0]}:⟨{parts[1]}⟩"
                    return s

                # Helper to parse flexible results
                def parse_res(res):
                    if not res: return []
                    if isinstance(res, list):
                        if len(res) > 0 and isinstance(res[0], dict) and 'result' in res[0]:
                            return res[0]['result']
                        return res
                    if isinstance(res, dict) and 'result' in res:
                        return res['result']
                    return []

                # Strategy 1: Lookup ID by Name (Most Robust)
                # Alias ID Lookup
                found_alias_obj = None # Keep original object
                found_alias_str = None # SQL Safe String

                try:
                    q_find_alias = f"SELECT id FROM entity WHERE name = '{alias}' LIMIT 1"
                    res_a = await self.db.query(q_find_alias)
                    rows = parse_res(res_a)
                    if rows:
                        found_alias_obj = rows[0]['id']
                        found_alias_str = safe_id(found_alias_obj)
                except Exception as e:
                    log(f"[Merge] Name lookup failed for alias '{alias}': {e}")

                # If name lookup failed, try ID variants
                if not found_alias_str:
                     candidates = []
                     # 1. Try Sanitized (Bracketed)
                     candidates.append(alias_id)
                     # 2. Try Raw (if it looks safe-ish)
                     if " " not in alias and not any(c in alias for c in "[]{}\\"):
                          candidates.append(f"entity:{alias}")
                     
                     for cand in candidates:
                         try:
                             # Check existence using SELECT ID
                             q_check_id = f"SELECT id FROM {cand}"
                             res_id = await self.db.query(q_check_id)
                             try:
                                 rows = parse_res(res_id)
                                 if rows:
                                     found_alias_obj = rows[0]['id']
                                     found_alias_str = safe_id(found_alias_obj)
                                     break
                             except: pass
                         except Exception as ex:
                             pass
                
                if not found_alias_str:
                    log(f"[Merge] Alias '{alias}' not found in DB. Skipping.")
                    continue

                log(f"[Merge] Found Alias Node: {found_alias_str}")

                # Canonical ID Lookup (or Create)
                found_canonical_str = None
                try:
                    q_find_canon = f"SELECT id FROM entity WHERE name = '{canonical}' LIMIT 1"
                    res_c = await self.db.query(q_find_canon)
                    rows = parse_res(res_c)
                    if rows:
                        found_canonical_str = safe_id(rows[0]['id'])
                except: pass

                if not found_canonical_str:
                    # If not found, use the sanitized ID we predicted
                    found_canonical_str = canonical_id # Already has brackets if _sanitize_id used
                    
                    # Create it just in case using UPSERT logic
                    try:
                         # Use raw formatting just to be safe if canonical_id was simple
                         if ":" in canonical_id and not "⟨" in canonical_id:
                             found_canonical_str = safe_id(canonical_id)
                         
                         await self.db.query(f"UPDATE {found_canonical_str} SET name='{canonical}', last_updated=time::now();")
                    except Exception as e:
                         log(f"[Merge] Failed to ensure canonical {found_canonical_str}: {e}")

                if found_alias_str == found_canonical_str:
                    log(f"[Merge] Same ID ({found_alias_str}). Skipping.")
                    continue
                
                log(f"[Merge] Merging {found_alias_str} -> {found_canonical_str}...")
                
                # Migrate Edges in ALL tables
                migrated_edges = 0
                for table in all_tables:
                    if table in ['entity', 'conversation', 'user', 'session']: continue
                    
                    try:
                        # Try to move incoming edges (where alias is SUBJECT/IN)
                        q_in = f"UPDATE {table} SET in={found_canonical_str} WHERE in={found_alias_str} RETURN NONE;"
                        await self.db.query(q_in)
                        
                        # Try to move outgoing edges (where alias is OBJECT/OUT)
                        q_out = f"UPDATE {table} SET out={found_canonical_str} WHERE out={found_alias_str} RETURN NONE;"
                        await self.db.query(q_out)
                    except Exception as ex:
                        # logger.warning(f"Edge migration failed for table {table}: {ex}")
                        pass
                
                # Finally deletion Alias Node
                try:
                    await self.db.delete(found_alias_str)
                    log(f"🧹 Merged Entity: {alias} -> {canonical}")
                    metrics["merged_aliases"] += 1
                except Exception as e:
                    log(f"[Merge] Failed to delete alias {found_alias_str}: {e}")
                
            except Exception as e:
                log(f"Failed to merge {alias}->{canonical}: {e}")
                
        return metrics, merge_logs

    async def prune_and_decay_graph(self):
        """
        Maintenance:
        1. Decay weights of all edges.
        2. Delete edges with low weight AND old timestamp.
        """
        if not self.db:
            await self.connect()
            
        try:
            # 1. Decay (Global) - reduce weight by 1%
            # Note: This scans all edges. For huge graphs, this needs sharding or limiting.
            # We'll just do it for 'likes', 'dislikes', etc. or generic if possible.
            # SurrealDB doesn't easily support "UPDATE ALL EDGES", we iterate distinct tables?
            # For now, let's assume we maintain a list of active relation types or just query INFO.
            
            # Simplified: Just decay commonly used tables for now
            relations = ["likes", "dislikes", "knows", "has", "is"]
            for rel in relations:
                await self.db.query(f"UPDATE {rel} SET weight = weight * 0.99 WHERE weight > 0.1")
                
            # 2. Culling
            # Delete if weight < 0.2 AND last_seen > 30 days
            cutoff_date = (datetime.now() - timedelta(days=30)).isoformat()
            for rel in relations:
                 await self.db.query(f"DELETE {rel} WHERE weight < 0.2 AND last_seen < '{cutoff_date}'")
                 
            logger.info("🍂 Graph pruned and decayed.")
        except Exception as e:
            logger.error(f"Pruning failed: {e}")

    # ==================== Search Operations ====================
    
    async def _mark_memories_hit(self, memory_ids: List[str]):
        """
        标记记忆被检索命中，仅增加计数
        
        Args:
           memory_ids: 被命中的记忆 ID 列表
        """
        if not self.db:
            await self.connect()
            
        for mem_id in memory_ids:
            try:
                # 仅增加命中计数，保持 status='active'
                await self.db.query(f"""
                    UPDATE {mem_id} SET 
                        hit_count = (hit_count ?? 0) + 1,
                        last_hit_at = time::now()
                """)
            except Exception as e:
                logger.warning(f"[_mark_memories_hit] Failed to mark {mem_id}: {e}")

    async def search(self, 
                    query_vector: List[float], 
                    character_id: str, 
                    limit: int = 10, 
                    threshold: float = 0.6) -> List[Dict]:
        """
        Vector Search on episodic_memory with Character Isolation.
        Uses HNSW index for fast approximate nearest neighbor search.
        
        注意: 只检索 status='active' 的记忆（已处理的有效记忆）
        """
        if not self.db:
            await self.connect()

        try:
            query = """
            SELECT 
                id, 
                content, 
                status, created_at, hit_count,
                vector::similarity::cosine(embedding, $query_vec) AS score 
            FROM episodic_memory 
            WHERE character_id = $character_id
              AND status = 'active'
              AND vector::similarity::cosine(embedding, $query_vec) > $threshold
            ORDER BY score DESC 
            LIMIT $limit;
            """

            results = self._parse_query_result(await self.db.query(query, {
                "query_vec": query_vector,
                "character_id": character_id,
                "limit": limit,
                "threshold": threshold
            }))
            
            # Parse results
            return results

        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []

    async def search_fulltext(self, 
                              query: str, 
                              character_id: str, 
                              limit: int = 10) -> List[Dict]:
        """
        Full-Text Search on episodic_memory using Substring Match (Robust for CJK).
        Note: Replaces BM25 with exact substring check to handle Chinese correctly without segmentation.
        """
        if not self.db:
            await self.connect()

        try:
            # ⚡ [Fix] Use string::lowercase + contains for Chinese support
            # Original Analyzer 'snowball(english)' fails on Chinese sentences (no spaces).
            sql = """
            SELECT id, 
                   content, 
                   status, created_at,
                   1.0 AS relevance 
            FROM episodic_memory
            WHERE string::lowercase(content) CONTAINS string::lowercase($query)
              AND character_id = $character_id
              AND status = 'active'
            ORDER BY created_at DESC
            LIMIT $limit;
            """

            results = self._parse_query_result(await self.db.query(sql, {
                "query": query,
                "character_id": character_id,
                "limit": limit
            }))
            
            return results

        except Exception as e:
            logger.error(f"❌ Full-text search error: {e}")
            return []

    async def search_hybrid(self, 
                           query: str,
                           query_vector: List[float],
                           character_id: str,
                           limit: int = 10,
                           vector_weight: float = 0.4,
                           initial_threshold: float = 0.6,
                           min_results: int = 3) -> List[Dict]:
        """
        Hybrid Search on episodic_memory: Vector + Full-Text with RRF fusion.
        Adaptive Threshold (Gradient Descent): If results < min_results, lower threshold and retry.
        """
        current_threshold = initial_threshold
        step_c = 0.1
        min_threshold = 0.2
        final_results = []
        
        loop_count = 0
        max_loops = 5  # Prevent infinite loops
        
        while loop_count < max_loops:
            # 1. 向量检索 (使用当前阈值)
            vec_results = await self.search(query_vector, character_id, limit * 2, threshold=current_threshold)
            
            # 2. 全文检索 (BM25, 阈值固定或由 DB 决定) - 只需要做一次其实，但为了简单放在循环里也可以（或者缓存）
            # Optimization: 只有第一次循环需要全文检索，后续只更新向量结果? 
            # 也可以每次都做，SurrealDB 很快.
            text_results = await self.search_fulltext(query, character_id, limit * 2)
            
            # 3. RRF Fusion
            scores = {}
            items = {}
            k = 60
            
            def process_list(lst, weight):
                for rank, item in enumerate(lst):
                    if not isinstance(item, dict): continue
                    item_id = str(item.get('id', rank))
                    if item_id not in scores:
                        scores[item_id] = 0
                        items[item_id] = item
                    scores[item_id] += weight / (k + rank + 1)

            process_list(vec_results, vector_weight)
            process_list(text_results, 1.0 - vector_weight)
            
            # Sort
            sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            results = []
            for item_id in sorted_ids[:limit]:
                item = items[item_id]
                item['hybrid_score'] = scores[item_id]
                results.append(item)
            
            final_results = results
            
            # Check sufficiency
            if len(final_results) >= min_results:
                if loop_count > 0:
                    logger.info(f"[Adaptive] Satisfied {len(final_results)} results at threshold {current_threshold:.2f}")
                break
                
            # Check minimum floor
            if current_threshold <= min_threshold:
                logger.debug(f"[Adaptive] Reached min threshold {min_threshold}, returning {len(final_results)} results")
                break
                
            # Gradient Descent
            prev_thresh = current_threshold
            current_threshold = max(min_threshold, current_threshold - step_c)
            logger.info(f"📉 [Adaptive Search] Results ({len(final_results)}) < {min_results}. Lowering threshold: {prev_thresh:.2f} -> {current_threshold:.2f}")
            
            loop_count += 1

        # ========== 标记命中记忆 (仅计数) ==========
        if final_results:
            try:
                memory_ids = [str(r['id']) for r in final_results if 'id' in r]
                if memory_ids:
                    await self._mark_memories_hit(memory_ids)
            except Exception as e:
                logger.warning(f"[search_hybrid] Failed to mark hits: {e}")
        
        return final_results

    # ==================== Graph Queries ====================

    async def get_character_memories(self, character_id: str, limit: int = 50) -> List[Dict]:
        """Get all memories observed by a character (graph traversal)."""
        if not self.db:
            await self.connect()
            
        try:
            # We want the EDGES that the character 'observes'.
            # character -> observes -> (edge:likes)
            # Fetching the target of 'observes' gives us the edge record.
            query = f"""
            SELECT ->observes->? AS memories
            FROM character:{character_id}
            LIMIT 1;
            """
            results = await self.db.query(query)
            
            if results and isinstance(results, list) and results[0].get('result'):
                memories = results[0]['result'][0].get('memories', [])
                return memories[:limit]
            return []
        except Exception as e:
            logger.error(f"Graph query error: {e}")
            return []

    async def get_user_facts(self, user_id: str, limit: int = 50) -> List[Dict]:
        """Get all facts about a specific user (graph traversal)."""
        if not self.db:
            await self.connect()
            
        try:
            query = f"""
            SELECT <-about<-fact.* AS facts
            FROM user_entity:{user_id}
            LIMIT 1;
            """
            results = await self.db.query(query)
            
            if results and isinstance(results, list) and results[0].get('result'):
                return results[0]['result']
            return []
        except Exception as e:
            logger.error(f"User fact query error: {e}")
            return []

    async def get_inspiration(self, character_id: str, limit: int = 3) -> List[Dict]:
        """Get random memories for inspiration/proactivity."""
        if not self.db:
            await self.connect()
            
        try:
            # Randomly select from 'episodic_memory' (Facts/Memories)
            # Use status != 'deleted' to include both active and archived (Long Term)
            # ⚡ Fix: DB-side 'ORDER BY rand()' is causing empty results in some versions.
            # We fetch a larger pool and shuffle in Python.
            pool_limit = limit * 5  # Fetch 5x pool (e.g. 50)
            
            query = f"""
            SELECT * FROM episodic_memory
            WHERE character_id = $character_id
              AND status != 'deleted'
            LIMIT $pool_limit;
            """
            
            results = await self.db.query(query, {"character_id": character_id, "pool_limit": pool_limit})
            
            # Parse results
            items = []
            if results and isinstance(results, list) and results[0].get('result'):
                items = results[0]['result']
            elif isinstance(results, list):
                # Flatten matching items
                for r in results:
                     if isinstance(r, dict) and 'id' in r: items.append(r)
            
            # Shuffle in Python
            import random
            random.shuffle(items)
            
            return items[:limit]
        except Exception as e:
            logger.error(f"Inspiration query error: {e}")
            return []

    async def get_all_conversations(self, character_id: str = None) -> List[Dict]:
        """Get all conversation records."""
        if not self.db:
            await self.connect()
        
        try:
            query = "SELECT * FROM conversation"
            params = {}
            if character_id:
                query += " WHERE character_id = $character_id"
                params["character_id"] = character_id
            
            query += " ORDER BY created_at DESC LIMIT 1000;" 
            
            results = await self.db.query(query, params)
             
            if results and isinstance(results, list) and results[0].get('result'):
                return results[0]['result']
            return []
        except Exception as e:
            logger.error(f"Get all conversations error: {e}")
            return []

    async def _get_entity_relations(self, entity_id: str) -> List[str]:
        """
        Fetch Outgoing and Incoming relations for an entity.
        Returns a list of formatted strings: "Subject relation Object"
        Applies Time-Decay: Filters out edges with effective strength < 0.1
        """
        try:
            # Formula: strength = base * (0.99 ^ days_elapsed)
            # Default base=0.8, Default decay_rate=0.01 (implicit in 0.99)
            
            # 1. Fetch Outgoing (entity -> edge -> target)
            q_out = f"""
            SELECT 
                type::table(id) as rel, 
                out.name as target,
                (base_strength OR 0.8) * math::pow(0.99, duration::days(time::now() - (last_mentioned OR created_at))) as strength
            FROM (SELECT VALUE ->? FROM {entity_id})
            WHERE 
                ((base_strength OR 0.8) * math::pow(0.99, duration::days(time::now() - (last_mentioned OR created_at)))) > 0.1
            ;"""
            
            res_out = await self.db.query(q_out)
            
            # 2. Fetch Incoming (source -> edge -> entity)
            q_in = f"""
            SELECT 
                type::table(id) as rel, 
                in.name as source,
                (base_strength OR 0.8) * math::pow(0.99, duration::days(time::now() - (last_mentioned OR created_at))) as strength
            FROM (SELECT VALUE <-? FROM {entity_id})
            WHERE 
                ((base_strength OR 0.8) * math::pow(0.99, duration::days(time::now() - (last_mentioned OR created_at)))) > 0.1
            ;"""
            
            res_in = await self.db.query(q_in)
            
            relations = []
            
            # Process Outgoing
            if res_out and isinstance(res_out, list) and res_out[0].get('result'):
                for r in res_out[0]['result']:
                    rel = r.get('rel')
                    target = r.get('target')
                    strength = r.get('strength', 0.0)
                    
                    if rel and target and rel not in ['observes', 'time_relation']:
                        # Optional: Include strength in debug or weak display?
                        # For AI, we just show the fact.
                         relations.append(f"-> {rel} -> {target}")

            # Process Incoming
            if res_in and isinstance(res_in, list) and res_in[0].get('result'):
                for r in res_in[0]['result']:
                    rel = r.get('rel')
                    source = r.get('source')
                    if rel and source and rel not in ['observes', 'time_relation']:
                        relations.append(f"<- {rel} <- {source}")

            return relations
        except Exception as e:
            logger.warning(f"Graph traversal error for {entity_id}: {e}")
            return []

    # ==================== Utilities ====================

    async def get_recent_conversations(self, character_id: str, limit: int = 20) -> List[Dict]:
        """Get recent conversation history for a character."""
        if not self.db:
            await self.connect()
            
        try:
            results = await self.db.query("""
                SELECT * FROM conversation
                WHERE character_id = $character_id
                ORDER BY created_at DESC
                LIMIT $limit;
            """, {"character_id": character_id, "limit": limit})
            
            if results and isinstance(results, list) and 'result' in results[0]:
                return results[0]['result']
            return []
        except Exception as e:
            logger.error(f"Failed to get conversations: {e}")
            return []

    async def get_stats(self, character_id: str = None) -> Dict:
        """Get memory statistics."""
        if not self.db:
            await self.connect()
            
        try:
            agent_filter = f"WHERE character_id = '{character_id}'" if character_id else ""
            
            # 统计 Episodic Memory (有效记忆) 和 Conversation Log (原始日志)
            mem_result = await self.db.query(f"SELECT count() FROM episodic_memory {agent_filter} GROUP ALL;")
            log_result = await self.db.query(f"SELECT count() FROM conversation_log {agent_filter} GROUP ALL;")
            
            # 解析 SurrealDB 返回格式（可能有多种格式）
            def parse_count(result):
                if not result:
                    return 0
                try:
                    # 新版 SurrealDB 返回格式
                    if isinstance(result, list) and len(result) > 0:
                        first = result[0]
                        if isinstance(first, dict):
                            if 'result' in first:
                                inner = first['result']
                                if isinstance(inner, list) and len(inner) > 0:
                                    return inner[0].get('count', 0)
                            elif 'count' in first:
                                return first['count']
                    return 0
                except:
                    return 0
            
            memories = parse_count(mem_result)
            logs = parse_count(log_result)
            
            # 仅在变化时打印日志，或降低日志级别，避免刷屏
            # logger.info(f"[Stats] Parsed: memories={memories}, logs={logs}")
            
            return {
                "entities": memories,    # 前端可能还在用 entities 这个字段名显示 "Memory"
                "conversations": logs
            }
        except Exception as e:
            logger.error(f"Stats error: {e}")
            return {"entities": 0, "conversations": 0}

    async def close(self):
        """Close connection and stop worker."""
        self.running = False
        if self.db:
            await self.db.close()
        logger.info("SurrealMemory closed")

