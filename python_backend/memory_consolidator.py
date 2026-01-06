
import json
import logging
import requests
import uuid
from typing import List, Dict, Any
from datetime import datetime
from qdrant_client import QdrantClient
from qdrant_client.http import models

# Configure logging
logger = logging.getLogger("MemoryConsolidator")

class MemoryConsolidator:
    def __init__(self, client: QdrantClient, config: Dict):
        self.client = client
        self.config = config
        self.consolidation_threshold = config.get("consolidation_threshold", 2)  # Default 2
        
    def consolidate_incrementally(self, new_facts: List[Dict], collection_name: str, user_name: str, char_name: str):
        """
        Incremental Consolidation Strategy:
        1. Take 'new_facts' (from Staging).
        2. Vector Search against Qdrant for semantic collisions (Conflict Detection).
        3. If collisions found, trigger LLM to Merge/Resolve.
        4. Return actions (Delete Old, Add New, Mark Processed).
        """
        print(f"[Consolidator] Processing {len(new_facts)} new facts for '{collection_name}'...")
        
        actions = {
            "processed_ids": [],      # Staging IDs to mark as done
            "qdrant_delete_ids": [],  # Old Qdrant Vectors to delete
            "new_facts": []           # New Merged Facts to Add
        }
        
        # Track which staging items we handled in this batch
        handled_staging_indices = set()
        
        # 1. Identify Conflicts (Clustering)
        # Simple algorithm: Check each new fact against existing DB.
        conflict_groups = []
        
        for idx, fact in enumerate(new_facts):
            if idx in handled_staging_indices:
                continue
                
            fact_text = fact["text"]
            fact_vector = fact.get("vector")
            
            # Search for similar existing memories
            # We want High Similarity (Conflict) -> e.g. > 0.75
            try:
                search_hits = self.client.query_points(
                    collection_name=collection_name,
                    query=fact_vector,
                    limit=5,
                    score_threshold=0.75,
                    with_payload=True
                ).points
            except Exception as e:
                print(f"[Consolidator] Search error: {e}")
                search_hits = []
                
            if not search_hits:
                # No conflict. This fact is unique enough.
                # Just mark it processed? No, we need to ensure it IS in Qdrant.
                # LiteMemory adds it to Qdrant BEFORE Staging. So it is already there.
                # But it might be the same vector we just found? 
                # Wait, if we just added it, self-match is possible!
                # We should filter out self-match if IDs match?
                # But LiteMemory generates NEW IDs for Staging that might differ from Qdrant IDs?
                # Actually, LiteMemory _save_fact_to_storage uses `vector_id` stored in staging.
                # So we can check valid ID.
                
                # If no *other* conflicts, we assume it's fine.
                actions["processed_ids"].append(fact["id"])
                continue
                
            # Conflict Found!
            # We need to resolve this `fact` vs `search_hits`
            existing_conflicts = []
            current_vector_id = fact.get("vector_id")
            
            for hit in search_hits:
                # Exclude self (if exact same ID)
                if hit.id == current_vector_id:
                    continue
                
                existing_conflicts.append({
                    "id": hit.id,
                    "text": hit.payload.get("text"),
                    "timestamp": hit.payload.get("timestamp"),
                    "score": hit.score
                })
            
            if not existing_conflicts:
                # Only matched self
                actions["processed_ids"].append(fact["id"])
                continue
                
            print(f"[Consolidator] ⚠️ Conflict Logic: '{fact_text}' conflicts with {len(existing_conflicts)} existing memories.")
            
            # Form a Conflict Group
            group = {
                "new_fact": fact,
                "existing": existing_conflicts
            }
            conflict_groups.append(group)
            handled_staging_indices.add(idx)

        # 2. Resolve Conflicts via LLM
        if not conflict_groups:
             return actions

        print(f"[Consolidator] Resolving {len(conflict_groups)} conflict groups...")
        
        for group in conflict_groups:
            # LLM Prompt
            resolution = self._llm_resolve_conflict(group["new_fact"], group["existing"], user_name, char_name)
            
            # Parse Resolution
            # Expectation: 
            # - potentially MERGED text
            # - instruction to delete OLD
            # - instruction to keep/delete NEW
            
            if resolution:
                # 1. Mark current staging fact as processed (we handled it)
                actions["processed_ids"].append(group["new_fact"]["id"])
                
                # 2. Delete ALL involved existing Qdrant vectors (we replace them)
                for exist in group["existing"]:
                    actions["qdrant_delete_ids"].append(exist["id"])
                    
                # 3. Add the resolved facts (usually 1 merged fact)
                # But we also need to delete the *current* vector of the new fact!
                # Because LiteMemory inserted it.
                # So if we Merge, we effectively replace (New + Old) -> Merged.
                # So we must delete 'New' vector too.
                actions["qdrant_delete_ids"].append(group["new_fact"]["vector_id"])
                
                actions["new_facts"].extend(resolution)
                
        return actions

    def _llm_resolve_conflict(self, new_fact, existing_facts, user_name, char_name):
        """
        Ask LLM: "I have a new fact and some similar old facts. 
        Are they duplicates? Contradictions? Or related?
        Consolidate them into a minimal set of truth."
        """
        prompt = f"""
You are a Memory Consolidator.
We have a NEW fact and some EXISTING memory fragments that are semantically similar.

**User**: {user_name}
**AI**: {char_name}

**NEW FACT**: ([{new_fact.get('timestamp')}]) "{new_fact.get('text')}"

**EXISTING FACTS**:
{json.dumps([f"({e['id']}) [{e.get('timestamp')}] {e.get('text')}" for e in existing_facts], indent=2, ensure_ascii=False)}

**GOAL**:
Consolidate these into the smallest, most accurate set of facts.
1. **Update**: If NEW updates OLD, keep NEW, discard OLD.
2. **Merge**: If they are parts of the same info, combine them.
3. **No Change**: If they are distinct topics, keep both (but phrase clearly).

Return a JSON List of strings (the consolidated facts).
Example: ["User likes apples and pears"]
"""
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a helpful JSON assistant."},
                    {"role": "user", "name": char_name, "content": prompt}  # 使用角色名
                ],
                "stream": False,
                "temperature": 0.0,
                "response_format": {'type': 'json_object'}
            }
            
            response = requests.post(
                f"{self.config['base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json=payload,
                timeout=30
            ) 
            
            content = response.json()['choices'][0]['message']['content'].strip()
            # Cleanup markdown
            if "```" in content:
                content = content.replace("```json", "").replace("```", "")
            
            results = json.loads(content)
            
            # Convert strings to Fact dicts (add metadata)
            structured_results = []
            for text in results:
                structured_results.append({
                    "text": text,
                    "importance": new_fact.get("importance", 1), # Inherit or recalculate
                    "emotion": new_fact.get("emotion", "neutral"),
                    "timestamp": datetime.now().isoformat() # Updated time
                })
                
            print(f"[Consolidator] Resolved -> {len(structured_results)} facts")
            return structured_results
            
        except Exception as e:
            print(f"[Consolidator] LLM Error: {e}")
            return [new_fact] # Fallback: Just keep the new one

