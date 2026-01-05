
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

from fact_extractor import FactExtractor


from memory_consolidator import MemoryConsolidator

class LiteMemory:
    def __init__(self, config: Dict, character_id: str = "hiyori"):
        """
        Dual-layer memory architecture:
        - User memory: Shared across all AI characters
        - Character memory: Isolated per AI character
        
        config: {
            "qdrant_path": "./lite_memory_db", 
            "openai_base_url": "...",
            "api_key": "...",
            "embedder_model": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja"
        }
        character_id: Unique identifier for the AI character (e.g., "hiyori", "aria")
        """
        self.config = config
        self.character_id = character_id
        
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
        
        # 1. Initialize Qdrant (Local persistent)
        self.client = QdrantClient(path=config.get("qdrant_path", "./lite_memory_db"))
        
        # 2. Initialize Embedder (Local with Auto-Download)
        embedder_path_name = config.get("embedder_model")
        
        # Resolve Repo ID for download (snapshot_download needs full ID, but config might be short alias)
        repo_id = embedder_path_name
        if repo_id == "paraphrase-multilingual-MiniLM-L12-v2":
            repo_id = "sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2"
        elif "/" not in repo_id:
             # Heuristic: If complex enough model, default to sentence-transformers? 
             # Or just hope user provides full ID for others.
             # For now, we only explicit fix the default.
             pass

        # Local folder name: Use the basename (e.g. "paraphrase-multilingual-MiniLM-L12-v2")
        # cleanly handled in models/ directory without organization prefix
        model_folder_name = repo_id.split("/")[-1]

        # Determine base path of this script
        base_dir = os.path.dirname(os.path.abspath(__file__))
        # Go up one level to project root, then into 'models'
        local_embedder_path = os.path.abspath(os.path.join(base_dir, "..", "models", model_folder_name))
        
        print(f"[LiteMemory] Local model path target: {local_embedder_path}")

        if os.path.exists(local_embedder_path) and os.listdir(local_embedder_path):
             print(f"[LiteMemory] ✅ Found existing local embedder model.")
        else:
             print(f"[LiteMemory] ⬇️ Local embedder not found. Downloading to {local_embedder_path}...")
             try:
                 snapshot_download(repo_id=repo_id, local_dir=local_embedder_path)
                 print(f"[LiteMemory] Download complete.")
             except Exception as e:
                 print(f"[LiteMemory] ⚠️ Download failed: {e}. Attempting fallback load from cache/hub...")
                 pass

        # If download succeeded or files existed, use local path. Otherwise fallback to ID
        if os.path.exists(local_embedder_path) and os.listdir(local_embedder_path):
            target_path = local_embedder_path
        else:
            target_path = embedder_path_name

        print(f"[LiteMemory] Loading embedder from: {target_path} ...")
        self.encoder = SentenceTransformer(target_path)
        self.embedding_size = self.encoder.get_sentence_embedding_dimension()
        print(f"[LiteMemory] Embedder loaded. Dim: {self.embedding_size}")
        
        # 3. Initialize Fact Extractor
        self.fact_extractor = FactExtractor(
            api_key=config["api_key"],
            base_url=config["openai_base_url"]
        )
        
        # 4. Initialize Consolidator
        self.consolidator = MemoryConsolidator(self.client, config)

        # 5. Background Queue
        # 5. Background Queue
        self.queue = Queue()
        self.running = True
        self.worker_thread = Thread(target=self._worker_loop, daemon=True)
        self.worker_thread.start()
        
        # 6. Initialize both collections and backup files
        self._init_dual_collections()
        
        print(f"[LiteMemory] Initialization complete.")

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
            search_result = self.client.query_points(
                collection_name=collection_name,
                query=query_vector,
                limit=limit,
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

    def add_memory_async(self, user_input: str, ai_response: str, user_name: str = "User", char_name: str = "AI"):
        """
        Fire-and-forget: Add task to queue
        """
        print(f"[LiteMemory] Enqueuing memory task. Input len: {len(user_input)} User: {user_name} Char: {char_name}")
        task = {
            "type": "add",
            "user_input": user_input,
            "ai_response": ai_response,
            "user_name": user_name,
            "char_name": char_name,
            "timestamp": datetime.now().isoformat()
        }
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
            except Exception as e:
                print(f"[LiteMemory] Worker error: {e}")
                import traceback
                traceback.print_exc()
            finally:
                self.queue.task_done()

    def _process_add_task(self, task):
        user_input = task["user_input"]
        ai_response = task["ai_response"]
        user_name = task.get("user_name", "User")
        char_name = task.get("char_name", "AI")
        
        print(f"[LiteMemory] Processing Add Task. User: '{user_input[:30]}...' (Names: {user_name}/{char_name})")
        
        # === DUAL-CHANNEL FACT EXTRACTION ===
        
        # Channel 1: User facts (from user_input only) → user_memory
        print("[LiteMemory] [Channel 1] Extracting USER facts...")
        # Note: We need to update FactExtractor.extract signature too
        user_facts = self.fact_extractor.extract(user_input, ai_response, user_name)
        print(f"[LiteMemory] [Channel 1] Found {len(user_facts)} USER facts: {user_facts}")
        
        # Channel 2: Conversation facts (topics discussed) → character_memory
        print("[LiteMemory] [Channel 2] Extracting CONVERSATION facts...")
        conversation_facts = self._extract_conversation_facts(user_input, ai_response, user_name, char_name)
        print(f"[LiteMemory] [Channel 2] Found {len(conversation_facts)} CONVERSATION facts: {conversation_facts}")
        
        # Process user facts → user_memory
        for fact in user_facts:
            self._process_and_save_fact(
                fact=fact,
                target_collection=self.user_collection_name,
                target_backup=self.user_backup_file,
                fact_source="user",
                task=task,
                user_input=user_input
            )
        
        # Process conversation facts → character_memory  
        for fact in conversation_facts:
            self._process_and_save_fact(
                fact=fact,
                target_collection=self.character_collection_name,
                target_backup=self.character_backup_file,
                fact_source="character",
                task=task,
                user_input=user_input
            )

        # === 3. Periodically Consolidate ===
        # Pass names to consolidator explicitly or via task context? 
        # Consolidator processes BUFFER, so it might handle mixed names.
        # But for resolving "User", passing current name helps context.
        self._handle_consolidation(self.user_collection_name, self.user_backup_file, user_name, char_name)
        self._handle_consolidation(self.character_collection_name, self.character_backup_file, user_name, char_name)

    def _handle_consolidation(self, collection_name: str, backup_file: str, user_name: str, char_name: str):
        """
        Check and execute consolidation if needed.
        Handles the result (Upserting new consolidated facts AND removing old ones from disk).
        """
        result = self.consolidator.check_and_consolidate(collection_name, self.character_id, user_name, char_name)
        
        if result:
            # 1. Save New Facts
            if result.get("new_facts"):
                new_facts = result["new_facts"]
                print(f"[LiteMemory] Consolidating {len(new_facts)} facts for {collection_name}...")
                
                for fact_text in new_facts:
                    if isinstance(fact_text, str):
                        self._save_consolidated_fact(fact_text, collection_name, backup_file)
            
            # 2. Cleanup Old Facts from Disk (Critical for avoiding duplicates in backup)
            if result.get("ids_to_delete"):
                self._delete_from_disk(result["ids_to_delete"], backup_file)

    def _save_consolidated_fact(self, text: str, collection_name: str, backup_file: str):
        """
        Directly save a fact without LLM conflict check (assumed clean).
        """
        try:
            # Embed
            vector = self.encoder.encode(text).tolist()
            new_id = str(uuid.uuid4())
            timestamp = datetime.now().isoformat()
            
            # Upsert
            self.client.upsert(
                collection_name=collection_name,
                points=[
                    models.PointStruct(
                        id=new_id,
                        vector=vector,
                        payload={
                            "text": text,
                            "type": "consolidated_fact",
                            "timestamp": timestamp,
                            "source": "consolidation"
                        }
                    )
                ]
            )
            
            # Backup
            self._save_to_disk({
                "id": new_id,
                "text": text,
                "vector": vector,
                "timestamp": timestamp,
                "meta": {"source": "consolidation"}
            }, backup_file)
            
            print(f"[LiteMemory] Saved consolidated fact: {text}")
            
        except Exception as e:
            print(f"[LiteMemory] Error saving consolidated fact: {e}")
    
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
                    {"role": "system", "content": "You are a conversation memory extractor."},
                    {"role": "user", "content": prompt}
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
    
    def _process_and_save_fact(self, fact: str, target_collection: str, 
                                target_backup: str, fact_source: str,
                                task: Dict, user_input: str):
        """Process a single fact: check duplicates, resolve conflicts, and save"""
        print(f"[LiteMemory] Processing fact for {target_collection}: '{fact}'")

        # 2. Duplicate & Conflict Detection
        fact_vector = self.encoder.encode(fact).tolist()
        
        existing = self.client.query_points(
            collection_name=target_collection,
            query=fact_vector,
            limit=5,
            score_threshold=0.6  # Lower threshold to catch potential merge candidates
        ).points
        
        # Default action: Add the new fact
        final_fact_text = fact
        ids_to_delete = []
        should_save = True

        if existing:
            print(f"[LiteMemory] Found {len(existing)} similar existing memories.")
            
            # Check for near-duplicates (very high similarity)
            is_duplicate = False
            for hit in existing:
                if hit.score >= 0.98:  # Extremely similar, likely a duplicate
                    print(f"[LiteMemory] DUPLICATE DETECTED (score: {hit.score:.3f}). Skipping: '{fact}'")
                    is_duplicate = True
                    should_save = False
                    break
            
            if not is_duplicate:
                # LLM Analysis for Conflicts, Merges, or Redundancy
                context_facts = [{"id": hit.id, "text": hit.payload["text"], "score": hit.score} 
                                for hit in existing]
                
                if context_facts:
                    print("[LiteMemory] Analyzing relationship with existing facts (LLM)...")
                    analysis = self._analyze_fact_interaction(fact, context_facts)
                    
                    action = analysis.get("action", "ADD")
                    ids_to_delete = analysis.get("delete_ids", [])
                    merged_text = analysis.get("merged_text")
                    
                    print(f"[LiteMemory] Analysis Result: {action}")
                    
                    if action == "SKIP":
                        print(f"[LiteMemory] Fact deemed redundant or skipped.")
                        should_save = False
                    elif action == "REPLACE":
                        print(f"[LiteMemory] Replacing existing facts {ids_to_delete}.")
                    elif action == "MERGE":
                        if merged_text:
                            final_fact_text = merged_text
                            print(f"[LiteMemory] Merging into: '{final_fact_text}'")
                        else:
                            print("[LiteMemory] Warning: MERGE action missing 'merged_text'. Falling back to ADD.")
                    elif action == "ADD":
                        pass # Default behavior

        # Execute Deletions
        if ids_to_delete:
            print(f"[LiteMemory] Deleting obsolete memories: {ids_to_delete}")
            # Qdrant Delete
            self.client.delete(
                collection_name=target_collection,
                points_selector=models.PointIdsList(points=ids_to_delete)
            )
            # Disk Delete (Sync)
            self._delete_from_disk(ids_to_delete, target_backup)

        # Execute Save (Upsert)
        if should_save:
            # Re-embed if text changed (Merge case)
            if final_fact_text != fact:
                fact_vector = self.encoder.encode(final_fact_text).tolist()
            
            new_id = str(uuid.uuid4())
            print(f"[LiteMemory] Upserting fact ID: {new_id}")
            
            # Write to Qdrant
            self.client.upsert(
                collection_name=target_collection,
                points=[
                    models.PointStruct(
                        id=new_id,
                        vector=fact_vector,
                        payload={
                            "text": final_fact_text,
                            "user_input": user_input,
                            "timestamp": task["timestamp"],
                            "type": "fact",
                            "source": fact_source
                        }
                    )
                ]
            )

            # Write to JSONL Backup
            self._save_to_disk({
                "id": new_id,
                "text": final_fact_text,
                "vector": fact_vector,
                "timestamp": task["timestamp"],
                "meta": {"user_input": user_input, "source": fact_source, "replaced_ids": ids_to_delete}
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
                    {"role": "system", "content": "You are a Knowledge Graph consistency manager. Output JSON only."},
                    {"role": "user", "content": prompt}
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
