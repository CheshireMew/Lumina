
import os
import json
import time
import asyncio
import uuid
import requests
from typing import List, Dict, Optional
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models
from sentence_transformers import SentenceTransformer
from huggingface_hub import snapshot_download
from queue import Queue
from threading import Thread

import logging

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("LiteMemory")

from fact_extractor_legacy import FactExtractor
from memory_consolidator_legacy import MemoryConsolidator
from time_indexed_memory import TimeIndexedMemory

class LiteMemory:
    def __init__(self, config: Dict, character_id: str = "hiyori"):
        """
        Dual-layer memory architecture:
        - User memory: Shared across all AI characters
        - Character memory: Isolated per AI character
        
        config: {
            "qdrant_path": "./lite_memory_db", 
            "sqlite_path": "./memory_db/lumina_memory.db",
            "openai_base_url": "...",
            "api_key": "...",
            "embedder_model": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja"
        }
        character_id: Unique identifier for the AI character (e.g., "hiyori", "aria")
        """
        self.config = config
        self.character_id = character_id
        
        # Thresholds (Configurable)
        self.batch_threshold = config.get("batch_threshold", 5) # Default 5 (was 20)
        self.consolidation_threshold = config.get("consolidation_threshold", 2) # Default 2 (was 10)
        
        # Dual collection names
        self.user_collection_name = "memory_user"  # Shared across all characters
        self.character_collection_name = f"memory_{character_id}"  # Per-character
        
        # Ensure backup directory exists
        backup_dir = "memory_backups"
        os.makedirs(backup_dir, exist_ok=True)
        
        # Dual backup files
        self.user_backup_file = os.path.join(backup_dir, "user_memory.jsonl")
        self.character_backup_file = os.path.join(backup_dir, f"{character_id}_memory.jsonl")
        
        print(f"[LiteMemory] === Dual-Layer Memory Architecture ===")
        print(f"[LiteMemory] Character: {character_id}")
        
        # 0. Initialize SQLite Time-Indexed Memory (SQL Layer)
        sqlite_path = config.get("sqlite_path", "./memory_db/lumina_memory.db")
        self.sql_db = TimeIndexedMemory(sqlite_path)
        print(f"[LiteMemory] SQLite initialized at: {sqlite_path}")

        # 1. Initialize Qdrant (Local persistent)
        self.client = QdrantClient(path=config.get("qdrant_path", "./lite_memory_db"))
        
        # 2. Initialize Embedder (Local with Auto-Download)
        embedder_path_name = config.get("embedder_model") or config.get("embedder")
        
        # Resolve Repo ID for download
        repo_id = embedder_path_name
        if not repo_id:
             repo_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        
        if repo_id == "paraphrase-multilingual-MiniLM-L12-v2":
            repo_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"

        # Local folder name logic
        model_folder_name = repo_id.split("/")[-1]
        base_dir = os.path.dirname(os.path.abspath(__file__))
        local_embedder_path = os.path.abspath(os.path.join(base_dir, "..", "models", model_folder_name))
        
        # Determine target path
        if os.path.exists(local_embedder_path) and os.listdir(local_embedder_path):
             print(f"[LiteMemory] ✅ Found existing local embedder: {local_embedder_path}")
             target_path = local_embedder_path
        else:
             print(f"[LiteMemory] ⬇️ Local embedder not found. Downloading...")
             try:
                 snapshot_download(repo_id=repo_id, local_dir=local_embedder_path)
                 target_path = local_embedder_path
             except Exception:
                 target_path = embedder_path_name or repo_id # Fallback

        # --- MODEL CACHING LOGIC ---
        if not hasattr(LiteMemory, "_encoder_cache"):
            LiteMemory._encoder_cache = {}

        if target_path in LiteMemory._encoder_cache:
            print(f"[LiteMemory] ⚡ Using CACHED embedder from: {target_path}")
            self.encoder = LiteMemory._encoder_cache[target_path]
        else:
            print(f"[LiteMemory] 🐢 Loading embedder from disk: {target_path} ...")
            self.encoder = SentenceTransformer(target_path)
            LiteMemory._encoder_cache[target_path] = self.encoder
            
        self.embedding_size = self.encoder.get_sentence_embedding_dimension()
        print(f"[LiteMemory] Embedder loaded. Dim: {self.embedding_size}")

        # 2.5 Ensure Collections Exist
        self._init_collections()
        
        # 3. Initialize Fact Extractor
        base_url = config.get("openai_base_url") or config.get("base_url")
        self.fact_extractor = FactExtractor(
            api_key=config.get("api_key"),
            base_url=base_url
        )
        
        # 4. Initialize Consolidator
        self.consolidator = MemoryConsolidator(self.client, config)

        # 5. Background Queue
        self.queue = Queue()
        self.running = True
        self.worker_thread = Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        # 6. Startup Recovery Check
        self._startup_recovery()

    def _init_collections(self):
        """Ensure necessary Qdrant collections exist."""
        for col_name in [self.character_collection_name, self.user_collection_name]:
            try:
                self.client.get_collection(col_name)
            except Exception:
                print(f"[LiteMemory] 🆕 Collection '{col_name}' not found. Creating...")
                try:
                    self.client.create_collection(
                        collection_name=col_name,
                        vectors_config=models.VectorParams(
                            size=self.embedding_size,
                            distance=models.Distance.COSINE
                        )
                    )
                    print(f"[LiteMemory] ✅ Collection '{col_name}' created.")
                except Exception as e:
                    print(f"[LiteMemory] ❌ Failed to create collection '{col_name}': {e}")

    def search_hybrid(self, query: str, limit: int = 10, empower_factor: float = 0.5) -> List[Dict]:
        """
        Hybrid Search: Vector (Semantic) + SQLite FTS (Keyword)
        Combined using Reciprocal Rank Fusion (RRF).
        
        Args:
            query: User's search query.
            limit: Number of results to return.
            empower_factor: (Unused for simple RRF, but kept for future weighting)
            
        Returns:
            List of memory objects sorted by hybrid score.
        """
        print(f"[LiteMemory] Hybrid Search for: '{query}'")
        
        # 1. Vector Search (Qdrant) - Semantic Recall
        # Search both Character and User collections
        vector_results = []
        try:
            query_vector = self.encoder.encode(query).tolist()
            for col in [self.character_collection_name, self.user_collection_name]:
                # ✅ Apply character_id filter ONLY to character specific collection
                # User collection is SHARED across all characters.
                query_filter = None
                if self.character_id and col == self.character_collection_name:
                    query_filter = models.Filter(
                        must=[
                            models.FieldCondition(
                                key="character_id",
                                match=models.MatchValue(value=self.character_id)
                            )
                        ]
                    )
                
                res = self.client.query_points(
                    collection_name=col,
                    query=query_vector,
                    limit=limit * 2, # Fetch more for re-ranking
                    with_payload=True,
                    query_filter=query_filter
                ).points
                vector_results.extend(res)
        except Exception as e:
            print(f"[LiteMemory] Vector search failed: {e}")

        # 2. Keyword Search (SQLite FTS) - Precision Recall
        keyword_results = []
        try:
            # Search specific character + user ('user' char_id in sqlite)
            # We search ONE time per character ID?
            # SQLite 'character_id' field stores 'hiyori' or 'user'.
            # We want both.
            # TODO: Update TimeIndexedMemory to support multiple char_ids OR call twice.
            # Calling twice is easier.
            
            keyword_results.extend(self.sql_db.get_memories_by_keyword(self.character_id, query, limit * 2))
            # keyword_results.extend(self.sql_db.get_memories_by_keyword("user", query, limit * 2)) # REMOVED: User facts are owned by character, so the first call covers them. 'user' ID doesn't exist.
            
        except Exception as e:
            print(f"[LiteMemory] Keyword search failed: {e}")

        # 3. Reciprocal Rank Fusion (RRF)
        # RRF Score = 1 / (k + rank)
        k = 60
        scores = {} # id -> score
        memory_map = {} # id -> memory_obj
        
        # Process Vector Results
        for rank, item in enumerate(vector_results):
            mem_id = item.id
            if mem_id not in scores:
                scores[mem_id] = 0.0
                # Normalize Qdrant/SQLite format differences
                memory_map[mem_id] = {
                    "id": mem_id,
                    "text": item.payload.get("text"),
                    "timestamp": item.payload.get("timestamp"),
                    "score": item.score, # Original vector score
                    "source": "vector",
                    "payload": item.payload
                }
            
            scores[mem_id] += 1.0 / (k + rank + 1)

        # Process Keyword Results
        for rank, item in enumerate(keyword_results):
            mem_id = item["id"]
            if mem_id not in scores:
                scores[mem_id] = 0.0
                memory_map[mem_id] = {
                    "id": mem_id,
                    "text": item["content"],
                    "timestamp": item["created_at"],
                    "score": 0.0, # Will be RRF score
                    "source": "keyword",
                    "payload": json.loads(item["metadata"]) if isinstance(item["metadata"], str) else item["metadata"]
                }
            
            scores[mem_id] += 1.0 / (k + rank + 1)

        # 3.5. Weighted Re-ranking (Time & Importance)
        # Apply Time Decay and Importance Boost to the RRF scores
        for mem_id, score in scores.items():
            mem = memory_map[mem_id]
            
            # A. Time Decay
            timestamp_str = mem.get("timestamp")
            score = self._apply_time_decay(score, timestamp_str)
            
            # B. Importance Boost
            # Importance is 1-10. We boost score by (1 + importance/20).
            # Max boost (10) = 1.5x. Min boost (1) = 1.05x.
            # If importance is missing, assume 1.
            try:
                # Payload might be dict or parsed JSON
                payload = mem.get("payload", {})
                if isinstance(payload, str):
                    try: payload = json.loads(payload)
                    except: payload = {}
                
                importance = int(payload.get("importance", 1))
            except:
                importance = 1
                
            importance_factor = 1.0 + (importance / 20.0)
            score *= importance_factor
            
            # Update Score
            scores[mem_id] = score

        # 4. Sort & Format
        combined = []
        for mem_id, score in scores.items():
            mem = memory_map[mem_id]
            mem["hybrid_score"] = score
            combined.append(mem)
        
        combined.sort(key=lambda x: x["hybrid_score"], reverse=True)
        top_results = combined[:limit]

        # 5. Graph Enrichment (Knowledge Graph)
        # Fetch 1-hop neighbors for the top results to provide deeper context
        try:
            top_ids = [m["id"] for m in top_results]
            if top_ids:
                print(f"[LiteMemory] Fetching graph context for {len(top_ids)} memories...")
                graph_context = self.sql_db.get_graph_context(top_ids, hops=1)
                
                # Add graph nodes as new results if they aren't already present
                # We give them a slightly lower score than the direct hit that spawned them
                existing_ids = set(top_ids)
                
                for context_item in graph_context:
                    # Ensure we don't duplicate if it's already in top results
                    if context_item['id'] in existing_ids:
                        continue
                        
                    existing_ids.add(context_item['id'])
                    
                    # Create a memory object for the graph node
                    graph_mem = {
                        "id": context_item["id"],
                        "text": f"[Related] {context_item['content']}", 
                        "timestamp": context_item.get("created_at"),
                        "score": 0.0, # Indicative
                        "hybrid_score": 0.0, # Lower priority
                        "source": "graph_association",
                        "payload": {"type": "graph_context", "relation": "associated"} 
                    }
                    top_results.append(graph_mem)
                    
        except Exception as e:
             print(f"[LiteMemory] Graph context fetch failed: {e}")

        print(f"[LiteMemory] Hybrid Search merged {len(vector_results)} vector + {len(keyword_results)} keyword -> {len(top_results)} results (with graph context).")
        return top_results

    def get_random_inspiration(self, limit: int = 3):
        """
        Returns random facts from consolidated memories to inspire AI's proactive conversation.
        Uses SQL RANDOM() to avoid expensive vector search.
        """
        try:
            # Use proper connection method
            with self.sql_db._get_connection() as conn:
                # Query random consolidated facts from this character
                # ⚡ Filter by character_id for multi-character support
                query = """
                    SELECT text, emotion, importance, created_at, channel, source_name
                    FROM facts_staging
                    WHERE consolidated = 1 AND character_id = ?
                    ORDER BY RANDOM()
                    LIMIT ?
                """
                cursor = conn.execute(query, (self.character_id, limit))
                rows = cursor.fetchall()
                
                results = []
                for row in rows:
                    results.append({
                        "content": row[0],
                        "emotion": row[1],
                        "importance": row[2],
                        "timestamp": row[3],
                        "channel": row[4],
                        "source": row[5] if row[5] else "Unknown"
                    })
                
                print(f"[LiteMemory] 🎲 Random Inspiration: Fetched {len(results)} facts")
                return results
                
        except Exception as e:
            print(f"[LiteMemory] Error fetching random inspiration: {e}")
            import traceback
            traceback.print_exc()
            return []

    def close(self):
        """Cleanup resources and stop background worker."""
        print(f"[LiteMemory] Closing instance for character: {self.character_id}")
        self.running = False
        # Push a None task to unblock the queue if it's waiting
        self.queue.put(None)
        
        if self.worker_thread.is_alive():
             self.worker_thread.join(timeout=2.0)
             
        # Qdrant local client explicit close if available (v1.something+)
        if hasattr(self.client, "close"):
            self.client.close()
        
        # Close SQLite connection if handled manually (TimeIndexedMemory handles its own context usually, but good to check)
        # self.sql_db.close() # Assuming TimeIndexedMemory doesn't hold a persistent open connection or handles it.
        
        print(f"[LiteMemory] Instance closed.")

    # === Graph / Event Sourcing Wrappers ===
    def add_event_log(self, content: str, event_type: str = "interaction") -> str:
        """Log an event to the immutable Event Store."""
        return self.sql_db.add_event(content, event_type, character_id=self.character_id)

    def add_knowledge_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        """Add a directed edge to the Knowledge Graph."""
        self.sql_db.add_graph_edge(source, target, relation, weight)

    def get_knowledge_context(self, memory_ids: List[str], hops: int = 1) -> List[Dict]:
        """Retrieve 1-hop graph context for given memories."""
        return self.sql_db.get_graph_context(memory_ids, hops)

    def _init_dual_collections(self):
        """Initialize both user and character collections and backup files"""
        print(f"[LiteMemory] Initializing dual collections...")
        # Create user backup file if it doesn't exist
        if not os.path.exists(self.user_backup_file):
            print(f"[LiteMemory] Creating user memory file: {self.user_backup_file}")
            with open(self.user_backup_file, 'w', encoding='utf-8') as f:
                pass  # Empty file
        
        # Create character backup file if it doesn't exist
        if not os.path.exists(self.character_backup_file):
            print(f"[LiteMemory] Creating character memory file: {self.character_backup_file}")
            with open(self.character_backup_file, 'w', encoding='utf-8') as f:
                pass  # Empty file
        
        # Ensure user collection exists
        self._ensure_collection(self.user_collection_name)
        
        # Ensure character collection exists
        self._ensure_collection(self.character_collection_name)
        
        print(f"[LiteMemory] Both collections initialized.")

    def _ensure_collection(self, collection_name: str):
        """Ensure a specific collection exists in Qdrant"""
        try:
            self.client.get_collection(collection_name)
            print(f"[LiteMemory] Collection '{collection_name}' already exists.")
        except Exception:
            print(f"[LiteMemory] Creating collection: {collection_name}")
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=models.VectorParams(
                    size=self.embedding_size,
                    distance=models.Distance.COSINE
                )
            )

    # ... (search method intentionally omitted here to avoid overwrite, already patched) ...


    def search(self, query: str, limit: int = 5) -> List[Dict]:
        """
        Dual-source search with Adaptive Thresholding (Gradient Degradation).
        Retries with lower thresholds if insufficient results are found.
        Thresholds: [0.60, 0.45, 0.30, 0.15]
        """
        thresholds = [0.60, 0.45, 0.30, 0.15]
        print(f"[LiteMemory] === Dual-Source Search (Adaptive) ===")
        print(f"[LiteMemory] Query: '{query}'")
        
        try:
            query_vector = self.encoder.encode(query).tolist()
            candidates_limit = limit * 2 # Fetch more for re-ranking
            
            final_candidates = []
            
            # Gradient Degradation Loop
            for threshold in thresholds:
                print(f"[LiteMemory] Trying threshold: {threshold}...")
                
                # Search from user memory
                user_results = self._search_collection(
                    self.user_collection_name, 
                    query_vector,
                    limit=candidates_limit,
                    score_threshold=threshold
                )
                
                # Search from character memory
                character_results = self._search_collection(
                    self.character_collection_name,
                    query_vector,
                    limit=candidates_limit,
                    score_threshold=threshold
                )
                
                # Merge unique results (deduplication by ID handled implicitly if we just take the fresh batch)
                # Since lower threshold query returns superset of higher threshold (mostly),
                # we can just use the results from the current successful tier.
                current_candidates = user_results + character_results
                
                print(f"[LiteMemory] Found {len(current_candidates)} candidates at threshold {threshold}")
                
                if len(current_candidates) >= limit:
                    final_candidates = current_candidates
                    break # Stop degrading if we have enough
                
                # If we are at the last threshold, take whatever we found
                final_candidates = current_candidates

            # If still nothing after all thresholds
            if not final_candidates:
                print("[LiteMemory] No memories found even at lowest threshold.")
                return []

            # Apply Time Decay & Re-rank
            weighted_results = []
            seen_ids = set()
            
            for item in final_candidates:
                if item['id'] in seen_ids:
                    continue
                seen_ids.add(item['id'])
                
                original_score = item['score']
                timestamp_str = item.get('timestamp')
                
                # Calculate decayed score
                decayed_score = self._apply_time_decay(original_score, timestamp_str)
                
                # Update score
                item['original_score'] = original_score
                item['score'] = decayed_score
                weighted_results.append(item)
            
            # Sort by new DECAYED score
            weighted_results.sort(key=lambda x: x['score'], reverse=True)
            
            # Return top results
            final_results = weighted_results[:limit]
            
            print(f"[LiteMemory] Search finished. Top result score: {final_results[0]['score'] if final_results else 'N/A'}")
            return final_results
            
        except Exception as e:
            print(f"[LiteMemory] Search error: {e}")
            import traceback
            traceback.print_exc()
            return []

    def _apply_time_decay(self, original_score: float, timestamp_str: str) -> float:
        """
        Apply time decay to the similarity score.
        Formula: Final = Original * (1 - decay_rate * hours_elapsed)
        Min Score Floor: Original * 0.8 (Don't reduce by more than 20%)
        """
        if not timestamp_str:
            return original_score
            
        try:
            # Parse timestamp (Handle ISO format)
            try:
                ts = datetime.fromisoformat(timestamp_str)
            except ValueError:
                # Fallback for potential legacy formats
                return original_score

            now = datetime.now()
            delta = now - ts
            hours_elapsed = delta.total_seconds() / 3600.0
            
            if hours_elapsed <= 0:
                return original_score
            
            # Decay Rate: How much importance is lost per hour?
            # e.g., 0.001 per hour => 1% lost every 10 hours
            # Let's be conservative: 0.05% per hour (~1.2% per day)
            decay_rate = 0.0005 
            
            decay_factor = 1.0 - (decay_rate * hours_elapsed)
            
            # Clamp factor: Don't let it drop below 0.8 (Max 20% penalty)
            # This ensures very relevant but old memories are still retrievable
            if decay_factor < 0.8:
                decay_factor = 0.8
                
            final_score = original_score * decay_factor
            
            # log debug only if significant change
            # print(f"  > Decay: {original_score:.4f} -> {final_score:.4f} (Age: {hours_elapsed:.1f}h)")
            
            return final_score
            
        except Exception as e:
            print(f"[LiteMemory] Time decay calc error: {e}")
            return original_score
    
    def _search_collection(self, collection_name: str, query_vector: List[float], 
                          limit: int, score_threshold: float) -> List[Dict]:
        """Helper: Search a specific collection"""
        try:
            # ⚡ Critical Fix: Filter by character_id if set
            # ⚡ Critical Fix: Filter by character_id if set
            query_filter = None
            if self.character_id and collection_name == self.character_collection_name:
                # Debug Logging for Filter
                # print(f"[LiteMemory] 🛡️ Filtering search by character_id: '{self.character_id}'")
                query_filter = models.Filter(
                    must=[
                        models.FieldCondition(
                            key="character_id",
                            match=models.MatchValue(value=self.character_id),
                        )
                    ]
                )
            else:
                 print(f"[LiteMemory] ⚠️ Warning: No character_id set for search filter!")

            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
                query_filter=query_filter, # ADD FILTER
                score_threshold=score_threshold
            ).points
            
            results = []
            for hit in search_result:
                results.append({
                    "id": hit.id,
                    "text": hit.payload.get("text"),
                    "score": hit.score,
                    "timestamp": hit.payload.get("timestamp"),
                    "source": collection_name  # Track which collection this came from
                })
            return results
        except Exception as e:
            print(f"[LiteMemory] Error searching {collection_name}: {e}")
            return []

    def add_memory_async(self, task: Dict):
        """
        Fire-and-forget: Add task to queue
        task dict should contain: user_input, ai_response, user_name, char_name, timestamp (optional)
        """
        if "type" not in task:
            task["type"] = "add"
        if "timestamp" not in task:
            task["timestamp"] = datetime.now().isoformat()
            
        print(f"[LiteMemory] Enqueuing memory add task.")
        self.queue.put(task)
        print(f"[LiteMemory] Task queued. Queue Size: {self.queue.qsize()}")

    def _worker_loop(self):
        print("[LiteMemory] Background worker started and waiting for tasks...")
        while self.running:
            task = self.queue.get()
            if task is None:
                print("[LiteMemory] Worker received stop signal.")
                self.queue.task_done()
                break
                
            print(f"[LiteMemory] Worker received task: {task['type']}")
            try:
                if task["type"] == "add":
                    self._process_add_task(task)
                elif task["type"] == "recover_extraction":
                    self._extract_facts_batch()
                elif task["type"] == "recover_consolidation":
                    # Use generic names for recovery actions if not provided
                    u_name = task.get("user_name", "User")
                    c_name = task.get("char_name", "AI")
                    # Determine collection
                    col = self.user_collection_name if task["channel"] == "user" else self.character_collection_name
                    self._handle_consolidation(col, task["channel"], u_name, c_name)
                    
            except Exception as e:
                print(f"[LiteMemory] Worker error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.queue.task_done()

    def _startup_recovery(self):
        """Check for backlog and enqueue recovery tasks."""
        print("[LiteMemory] 🔍 Checking for recovery tasks...")
        
        # Check Buffer
        try:
            count = self.sql_db.get_conversations_count(processed=False)
            if count >= self.batch_threshold:
                 print(f"[LiteMemory] ⚠️ Found {count} buffered conversations. Triggering extraction recovery.")
                 self.queue.put({"type": "recover_extraction", "timestamp": str(time.time())})
        except Exception as e:
            print(f"[LiteMemory] Recovery check failed (Buffer): {e}")

        # Check Staging
        try:
            for ch in ["user", "character"]:
                 c = self.sql_db.get_facts_count(channel=ch, consolidated=False)
                 if c >= self.consolidation_threshold:
                      print(f"[LiteMemory] ⚠️ Found {c} unconsolidated {ch} facts. Triggering consolidation recovery.")
                      self.queue.put({
                          "type": "recover_consolidation", 
                          "channel": ch, 
                          "timestamp": str(time.time()),
                          # Use config names if possible? But self.config might not have specific names. 
                          # Just use defaults.
                      })
        except Exception as e:
            print(f"[LiteMemory] Recovery check failed (Staging): {e}")

    
    def _save_fact_to_storage(self, fact: Dict, channel: str, collection_name: str, source_name: str):
        """Helper to save a newly extracted fact to Qdrant and Staging Table."""
        text = fact.get("text", "")
        if not text: return
        
        vector_id = str(uuid.uuid4())
        # Generate embedding
        vector = self.encoder.encode(text).tolist()
        
        # ✅ 确保 payload 包含 character_id
        fact_payload = {
            **fact,  # 保留原有字段
            "character_id": self.character_id,  # 添加 character_id
            "source_name": source_name,  # 添加 source_name
            "channel": channel  # 添加 channel
        }
        
        # 1. Upsert to Qdrant
        self.client.upsert(
            collection_name=collection_name,
            points=[models.PointStruct(
                id=vector_id,
                vector=vector,
                payload=fact_payload  # ✅ 使用增强后的 payload
            )]
        )
        
        # 2. Add to Staging
        # fact_id for staging table
        f_staging_id = str(uuid.uuid4())
        self.sql_db.add_fact_staging(
            fact_id=f_staging_id, 
            text=text,
            emotion=fact.get("emotion", "neutral"),
            importance=fact.get("importance", 1),
            timestamp=fact.get("timestamp", datetime.now().isoformat()),
            channel=channel,
            source_name=source_name,
            vector_id=vector_id,
            character_id=self.character_id  # ⚡ 添加角色 ID
        )

    def _extract_facts_batch(self):
        """
        Phase 2 Logic: Batch Fact Extraction
        Triggered when unprocessed conversations >= 20.
        """
        try:
            # 1. Check Count
            unprocessed_count = self.sql_db.get_conversations_count(processed=False)
            if unprocessed_count < self.batch_threshold: 
                return

            print(f"[LiteMemory] Triggering Batch Extraction (Backlog: {unprocessed_count})...")
            
            # 2. Fetch limit 20
            conversations = self.sql_db.get_unprocessed_conversations(limit=20)
            if not conversations:
                return
                
            # Assume single user/char context for now (or taking from first item)
            user_name = conversations[0]['user_name']
            char_name = conversations[0]['char_name']
            
            # 3. Channel 1: User Facts (Concat all user inputs)
            batch_context_user = "\n".join([
                f"[{c['timestamp']}] {c['user_name']}: {c['user_input']}" 
                for c in conversations
            ])
            
            print("[LiteMemory] [Channel 1] Batch extracting USER facts...")
            user_facts = self.fact_extractor.extract_batch(batch_context_user, focus="user", person_name=user_name)
            
            # Save to Qdrant + Staging
            for fact in user_facts:
                self._save_fact_to_storage(fact, "user", self.user_collection_name, user_name)

            # 4. Channel 2: Conversation Facts (Topics)
            batch_context_conv = "\n".join([
                f"[{c['timestamp']}] {c['user_name']}: {c['user_input']}\n{c['char_name']}: {c['ai_response']}"
                for c in conversations
            ])
            
            print("[LiteMemory] [Channel 2] Batch extracting CONVERSATION topics...")
            conv_facts = self.fact_extractor.extract_batch(batch_context_conv, focus="conversation", person_name=char_name)
            
            # Save to Qdrant + Staging
            for fact in conv_facts:
                self._save_fact_to_storage(fact, "character", self.character_collection_name, char_name)
                
            # 5. Mark as Processed
            batch_id = str(uuid.uuid4())
            conv_ids = [c['id'] for c in conversations]
            self.sql_db.mark_conversations_processed(conv_ids, batch_id)
            print(f"[LiteMemory] Batch {batch_id} processed ({len(conv_ids)} conversations).")
            
            # 6. Trigger Consolidation Check
            self._handle_consolidation(self.user_collection_name, "user", user_name, char_name)
            self._handle_consolidation(self.character_collection_name, "character", user_name, char_name)
            
        except Exception as e:
            print(f"[LiteMemory] Batch extraction error: {e}")
            import traceback
            traceback.print_exc()

    def _handle_consolidation(self, collection_name: str, channel: str, user_name: str, char_name: str):
        """Phase 3: Trigger Incremental Consolidation"""
        # (This replaces the old method signature, so we need to be careful with callers if any exist besides _process)
        try:
            # Check staging count
            count = self.sql_db.get_facts_count(channel=channel, consolidated=False)
            if count < self.consolidation_threshold:
                return

            print(f"[LiteMemory] Triggering Consolidation for '{channel}' (Backlog: {count})...")
            
            # 1. Fetch new facts from Staging
            new_facts_rows = self.sql_db.get_unconsolidated_facts(channel, limit=10) # Process 10 at a time
            
            # Convert to list of dicts and ADD VECTORS (needed for search)
            new_facts = []
            for row in new_facts_rows:
                fact_dict = dict(row)
                fact_dict["vector"] = self.encoder.encode(fact_dict["text"]).tolist()
                new_facts.append(fact_dict)

            # 2. Call Consolidator
            # Note: Consolidator methods were updated to accept new signature
            result = self.consolidator.consolidate_incrementally(new_facts, collection_name, user_name, char_name)
            
            if not result:
                return

            # 3. Process Actions
            
            # A. Mark Staging as Consolidated
            processed_staging_ids = result.get("processed_ids", [])
            if processed_staging_ids:
                self.sql_db.mark_facts_consolidated(processed_staging_ids)

            # B. Delete Old Vectors from Qdrant
            delete_qdrant_ids = result.get("qdrant_delete_ids", [])
            if delete_qdrant_ids:
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=models.PointIdsList(points=delete_qdrant_ids)
                )
                print(f"[LiteMemory] Removed {len(delete_qdrant_ids)} obsolete vectors.")

            # C. Insert New Merged Facts
            new_facts_to_add = result.get("new_facts", [])
            for nf in new_facts_to_add:
                # We add them to Qdrant AND Staging (marked as consolidated)
                nv_id = str(uuid.uuid4())
                nv_vec = self.encoder.encode(nf["text"]).tolist()
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[models.PointStruct(
                        id=nv_id,
                        vector=nv_vec,
                        payload=nf
                    )]
                )
                
                # Add to staging but mark as consolidated immediately
                f_id = str(uuid.uuid4())
                self.sql_db.add_fact_staging(
                    fact_id=f_id,
                    text=nf["text"],
                    emotion=nf.get("emotion", "neutral"),
                    importance=nf.get("importance", 1),
                    timestamp=nf.get("timestamp"),
                    channel=channel,
                    source_name=user_name if channel=="user" else char_name,
                    vector_id=nv_id,
                    character_id=self.character_id  # ⚡ 添加角色 ID
                )
                self.sql_db.mark_facts_consolidated([f_id])
                
        except Exception as e:
            print(f"[LiteMemory] Consolidation error: {e}")
            import traceback
            traceback.print_exc()

    def _process_add_task(self, task):
        """
        New 3-Layer Implementation:
        1. Log to SQLite (Time Machine)
        2. Log to Event Store
        3. Add to Conversation Buffer
        4. Trigger Batch Extraction (if >= threshold)
        """
        user_input = task["user_input"]
        ai_response = task["ai_response"]
        user_name = task.get("user_name", "User")
        char_name = task.get("char_name", "AI")
        timestamp = task["timestamp"]
        
        print(f"[LiteMemory] Processing Add Task. User: '{user_input[:30]}...'")
        
        # === A. Save Raw Dialogue to SQLite (Time Machine) ===
        try:
            self.sql_db.add_memory(
                character_id=self.character_id,
                content=f"{user_name}: {user_input}",
                type="dialogue",
                created_at=timestamp,
                metadata={"role": "user", "name": user_name}
            )
            self.sql_db.add_memory(
                character_id=self.character_id,
                content=f"{char_name}: {ai_response}",
                type="dialogue",
                created_at=timestamp, 
                metadata={"role": "assistant", "name": char_name}
            )
            
            # === Event Sourcing Log ===
            try:
                self.add_event_log(f"{user_name}: {user_input} | {char_name}: {ai_response}", event_type="interaction")
            except Exception as e:
                print(f"[LiteMemory] Event Log Warning: {e}")
            
            # === B. Add to Conversation Buffer ===
            self.sql_db.add_conversation(user_name, char_name, user_input, ai_response, timestamp, character_id=self.character_id)
            print("[LiteMemory] Conversation buffered.")
            
            # === C. Trigger Pipeline ===
            self._extract_facts_batch()
            
        except Exception as e:
            print(f"[LiteMemory] Error in _process_add_task: {e}")
            import traceback
            traceback.print_exc()

    def _handle_consolidation(self, collection_name: str, channel: str, user_name: str, char_name: str):
        """Phase 3: Trigger Incremental Consolidation"""
        try:
            # Check staging count
            count = self.sql_db.get_facts_count(channel=channel, consolidated=False)
            if count < self.consolidation_threshold:
                return

            print(f"[LiteMemory] Triggering Consolidation for '{channel}' (Backlog: {count})...")
            
            # 1. Fetch new facts from Staging
            new_facts_rows = self.sql_db.get_unconsolidated_facts(channel, limit=10) # Process 10 at a time
            
            # Convert to list of dicts and ADD VECTORS
            new_facts = []
            for row in new_facts_rows:
                fact_dict = dict(row)
                if hasattr(self, 'encoder'):
                    fact_dict["vector"] = self.encoder.encode(fact_dict["text"]).tolist()
                new_facts.append(fact_dict)

            # 2. Call Consolidator
            result = self.consolidator.consolidate_incrementally(new_facts, collection_name, user_name, char_name)
            
            if not result:
                return

            # 3. Process Actions
            
            # A. Mark Staging as Consolidated
            processed_staging_ids = result.get("processed_ids", [])
            if processed_staging_ids:
                self.sql_db.mark_facts_consolidated(processed_staging_ids)

            # B. Delete Old Vectors from Qdrant
            delete_qdrant_ids = result.get("qdrant_delete_ids", [])
            if delete_qdrant_ids:
                self.client.delete(
                    collection_name=collection_name,
                    points_selector=models.PointIdsList(points=delete_qdrant_ids)
                )
                print(f"[LiteMemory] Removed {len(delete_qdrant_ids)} obsolete vectors.")

            # C. Insert New Merged Facts
            new_facts_to_add = result.get("new_facts", [])
            for nf in new_facts_to_add:
                nv_id = str(uuid.uuid4())
                nv_vec = self.encoder.encode(nf["text"]).tolist()
                
                self.client.upsert(
                    collection_name=collection_name,
                    points=[models.PointStruct(
                        id=nv_id,
                        vector=nv_vec,
                        payload=nf
                    )]
                )
                
                # Add to staging but mark as consolidated immediately
                f_id = str(uuid.uuid4())
                self.sql_db.add_fact_staging(
                    fact_id=f_id,
                    text=nf["text"],
                    emotion=nf.get("emotion", "neutral"),
                    importance=nf.get("importance", 1),
                    timestamp=nf.get("timestamp"),
                    channel=channel,
                    source_name=user_name if channel=="user" else char_name,
                    vector_id=nv_id,
                    character_id=self.character_id  # ⚡ 添加角色 ID
                )
                self.sql_db.mark_facts_consolidated([f_id])
                
        except Exception as e:
            print(f"[LiteMemory] Consolidation error: {e}")
            import traceback
            traceback.print_exc()
    
    def _extract_conversation_facts(self, user_input: str, ai_response: str, user_name: str, char_name: str) -> List[str]:
        """Extract facts about the conversation itself (topics discussed, context)"""
        prompt = f"""Extract key topics or facts from this conversation that {char_name} (the AI) should remember for context.

**Conversation:**
{user_name}: {user_input}
{char_name}: {ai_response}

**Focus on:**
- Topics discussed
- Questions asked
- Information shared (by either party)
- Context that would be useful for future conversations

**CRITICAL EXCLUSION:**
- DO NOT extract facts about {user_name}'s permanent profile (e.g. "{user_name} likes X"). These are handled by a separate system.
- DO NOT extract meta-commentary like "{char_name} asked...", "{user_name} mentioned...".
- Extract ONLY the SUBSTANCE of the conversation or JOINT EXPERIENCES.
- INCLUDE opinions or self-disclosures (e.g. "{char_name} loves summer too").

**Format:** Return a JSON list of short fact strings.
**Examples:**
- "Discussed Python programming"
- "{user_name} asked about machine learning"
- "Explained the concept of embeddings"
- "Agreed that summer is the best season"

**LANGUAGE RULE**: Output facts in the SAME LANGUAGE as the User's Input. (e.g. Chinese -> Chinese)

If nothing significant to remember about the CONVERSATION itself, return [].

If nothing significant to remember, return [].

Output (JSON only):
"""
        
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a conversation memory extractor."},
                    {"role": "user", "name": self.character_id, "content": prompt}  # 使用角色ID
                ],
                "stream": False,
                "temperature": 0.0
            }
            
            # DEBUG LOG
            print(f"[LiteMemory] [DEBUG] Extract Conversation Facts Prompt:\n{prompt}")
            
            response = requests.post(
                f"{self.config['openai_base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # DEBUG LOG
            print(f"[LiteMemory] [DEBUG] Extract Conversation Facts Result:\n{content}")
            
            # Clean up markdown
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            facts = json.loads(content)
            return facts if isinstance(facts, list) else []
            
        except Exception as e:
            print(f"[LiteMemory] Error extracting conversation facts: {e}")
            return []
    
    def _process_and_save_fact(self, fact_data: str | Dict, target_collection: str, 
                                target_backup: str, fact_source: str,
                                timestamp: str, user_input: str):
        """Process a single fact: check duplicates, resolve conflicts, and save"""
        
        # Parse metadata
        if isinstance(fact_data, dict):
            fact_text = fact_data.get("text", "").strip()
            emotion = fact_data.get("emotion", "neutral")
            importance = fact_data.get("importance", 1)
        else:
            fact_text = str(fact_data).strip()
            emotion = "neutral"
            importance = 1
            
        if not fact_text:
            return

        print(f"[LiteMemory] Processing fact for {target_collection}: '{fact_text}' (Imp:{importance}, Emo:{emotion})")

        # 2. Duplicate & Conflict Detection
        fact_vector = self.encoder.encode(fact_text).tolist()
        
        existing = self.client.query_points(
            collection_name=target_collection,
            query=fact_vector,
            limit=5,
            score_threshold=0.6,
            with_payload=True
        )
        
        should_save = True
        final_fact_text = fact_text
        ids_to_delete = []

        if existing and existing.points:
            # LLM Analysis for conflict resolution
            action, new_text, merged_ids = self._analyze_fact_interaction(fact_text, existing.points)
            
            if action == "SKIP":
                should_save = False
            elif action == "REPLACE":
                final_fact_text = new_text
                ids_to_delete = merged_ids
                # Delete old ones from disk and Qdrant
                if ids_to_delete:
                    print(f"[LiteMemory] Deleting obsolete memories (REPLACE): {ids_to_delete}")
                    self.client.delete(collection_name=target_collection, points_selector=models.PointIdsList(points=ids_to_delete))
                    self._delete_from_disk(ids_to_delete, target_backup)
            elif action == "MERGE":
                final_fact_text = new_text
                ids_to_delete = merged_ids
                # Delete old ones from disk and Qdrant
                if ids_to_delete:
                    print(f"[LiteMemory] Deleting obsolete memories (MERGE): {ids_to_delete}")
                    self.client.delete(collection_name=target_collection, points_selector=models.PointIdsList(points=ids_to_delete))
                    self._delete_from_disk(ids_to_delete, target_backup)
            # if ADD, do nothing special

        # Execute Save (Upsert)
        if should_save:
            # Re-embed if text changed (Merge case)
            if final_fact_text != fact_text:
                fact_vector = self.encoder.encode(final_fact_text).tolist()
            
            # Generate ID once for Dual-Write Consistency
            new_id = str(uuid.uuid4())
            
            print(f"[LiteMemory] Upserting fact ID: {new_id}")
            
            # 1. Dual-Write to SQLite (SSOT)
            try:
                # determine target character_id for Sqlite based on collection
                target_char_id = "user" if target_collection == self.user_collection_name else self.character_id
                
                self.sql_db.add_memory(
                    character_id=target_char_id,
                    content=final_fact_text,
                    type="fact",
                    created_at=timestamp,
                    importance=importance,
                    emotion=emotion,
                    source_id=None,
                    metadata={"source": fact_source, "user_input": user_input},
                    memory_id=new_id # Sync ID
                )
            except Exception as e:
                print(f"[LiteMemory] ⚠️ SQLite Write Failed: {e}")
            
            # 2. Write to Qdrant (Index)
            self.client.upsert(
                collection_name=target_collection,
                points=[
                    models.PointStruct(
                        id=new_id,
                        vector=fact_vector,
                        payload={
                            "text": final_fact_text,
                            "user_input": user_input,
                            "timestamp": timestamp,
                            "type": "fact",
                            "source": fact_source,
                            "emotion": emotion,
                            "importance": importance
                        }
                    )
                ]
            )

            # 3. Write to JSONL Backup (Legacy / Cold Storage)
            self._save_to_disk({
                "id": new_id,
                "text": final_fact_text,
                "vector": fact_vector,
                "timestamp": timestamp,
                "meta": {
                    "user_input": user_input, 
                    "source": fact_source, 
                    "replaced_ids": ids_to_delete,
                    "emotion": emotion,
                    "importance": importance
                }
            }, target_backup)
            
            print(f"[LiteMemory] ✅ SAVED: {final_fact_text}")


    def _save_to_disk(self, data: Dict, backup_file: str = None):
        """Save memory to disk backup file"""
        if backup_file is None:
            backup_file = self.character_backup_file  # Default to character backup
        
        try:
            print(f"[LiteMemory] Saving to disk: {backup_file}")
            with open(backup_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(data, ensure_ascii=False) + "\n")
            print(f"[LiteMemory] Appended to backup file: {backup_file}")
        except Exception as e:
            print(f"[LiteMemory] Disk save failed: {e}")

    def _delete_from_disk(self, delete_ids: List[str], backup_file: str = None):
        """Remove facts with specific IDs from the JSONL backup file (Rewrite)"""
        if not delete_ids:
            return
            
        if backup_file is None:
            backup_file = self.character_backup_file
            
        if not os.path.exists(backup_file):
            return

        try:
            print(f"[LiteMemory] Deleting {len(delete_ids)} records from disk: {backup_file}")
            
            # Read all lines
            start_time = time.time()
            kept_lines = []
            deleted_count = 0
            
            with open(backup_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Check if this record's ID is in the deletion list
                        if record.get("id") in delete_ids:
                            deleted_count += 1
                            continue # Skip -> Delete
                        kept_lines.append(line)
                    except json.JSONDecodeError:
                        kept_lines.append(line) # Keep corrupted lines to avoid data loss
            
            # Write back only if we actually deleted something to save IO
            if deleted_count > 0:
                with open(backup_file, "w", encoding="utf-8") as f:
                    for line in kept_lines:
                        f.write(line + "\n")
                
                duration = time.time() - start_time
                print(f"[LiteMemory] Disk cleanup complete. Removed {deleted_count} items in {duration:.4f}s.")
            else:
                print(f"[LiteMemory] No matching IDs found in disk backup to delete.")
            
        except Exception as e:
            print(f"[LiteMemory] Error deleting from disk: {e}")

    def close(self):
        """Release resources (Qdrant lock)"""
        print("[LiteMemory] Closing instance...")
        self.running = False
        self.queue.put(None) # Sentinel to unblock worker
        
        if self.worker_thread.is_alive():
            try:
                self.worker_thread.join(timeout=2.0)
            except Exception as e:
                print(f"[LiteMemory] Error joining thread: {e}")

        if hasattr(self, 'client'):
             try:
                 self.client.close()
                 print("[LiteMemory] Qdrant client closed.")
             except Exception as e:
                 print(f"[LiteMemory] Error closing client: {e}")


    def _analyze_fact_interaction(self, new_fact: str, existing_facts: List[Dict]) -> Dict:
        """
        Uses LLM to determine if the new fact interacts with existing facts.
        Returns a dict with action instructions.
        """
        if not existing_facts:
            return {"action": "ADD"}
            
        prompt = f"""
Analyze the relationship between the NEW FACT and the EXISTING FACTS.
Determine the appropriate action to maintain a concise and consistent knowledge base.

NEW FACT: "{new_fact}"

EXISTING FACTS:
{json.dumps(existing_facts, ensure_ascii=False, indent=2)}

Available Actions:
1. "ADD": The NEW FACT is unrelated to existing facts. Keep all.
2. "SKIP": The NEW FACT is already fully covered by an existing fact (Redundant). Do nothing.
3. "REPLACE": The NEW FACT conflicts with or updates an existing fact (e.g., "User is 25" vs "User is 26"). Delete the obsolete existing fact(s).
4. "MERGE": The NEW FACT adds to an existing list or concept (e.g., "Likes apples" + "Likes pears" -> "Likes apples and pears"). Delete the partial existing fact(s) and provide a new MERGED text.

Output JSON ONLY:
{{
  "action": "ADD" | "SKIP" | "REPLACE" | "MERGE",
  "delete_ids": ["id_to_delete_1", ...],   // IDs of existing facts to remove (for REPLACE or MERGE)
  "merged_text": "The new combined fact text" // ONLY for MERGE action
}}
"""
        
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a Knowledge Graph consistency manager. Output JSON only."},
                    {"role": "user", "name": self.character_id, "content": prompt}  # 使用角色ID
                ],
                "stream": False,
                "temperature": 0.0
            }
            
            headers = {
                "Authorization": f"Bearer {self.config['api_key']}",
                "Content-Type": "application/json"
            }
            
            response = requests.post(
                f"{self.config['openai_base_url']}/chat/completions",
                headers=headers,
                json=payload,
                timeout=10
            )
            
            # DEBUG LOG
            print(f"[LiteMemory] [DEBUG] Analyze Fact Interaction Prompt:\n{prompt}")
            
            if response.status_code == 200:
                content = response.json()['choices'][0]['message']['content'].strip()
                
                # DEBUG LOG
                print(f"[LiteMemory] [DEBUG] Analyze Fact Interaction Result:\n{content}")
                
                if content.startswith("```"):
                     content = content.replace("```json", "").replace("```", "").strip()
                result = json.loads(content)
                return result
            else:
                print(f"[LiteMemory] API Error: {response.text}")
            
        except Exception as e:
            print(f"[LiteMemory] Analysis failed: {e}")
            
        return {"action": "ADD"}


if __name__ == "__main__":
    pass
