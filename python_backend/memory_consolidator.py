
import json
import logging
import requests
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
        self.consolidation_threshold = 10  # Low for testing, production should be ~50
        
    def check_and_consolidate(self, collection_name: str, character_id: str, user_name: str = "User", char_name: str = "AI"):
        """
        Check if consolidation is needed and execute if threshold reached.
        """
        try:
            # 1. Count items
            count_result = self.client.count(collection_name=collection_name)
            count = count_result.count
            print(f"[Consolidator] Collection '{collection_name}' count: {count}")
            
            if count >= self.consolidation_threshold:
                print(f"[Consolidator] Threshold reached. Starting consolidation for {user_name} / {char_name}...")
                return self._perform_consolidation(collection_name, character_id, user_name, char_name)
                
        except Exception as e:
            print(f"[Consolidator] Check error: {e}")
        return None

    def _perform_consolidation(self, collection_name: str, character_id: str, user_name: str, char_name: str):
        """
        Execute the consolidation process:
        1. Fetch all memories
        2. LLM Merge/Resolve
        3. Atomic Update (Delete All + Insert New) 
        WARNING: "Delete All" is risky. Better to Delete specific IDs.
        Strategy: We will consolidate the *entire* buffer if small, or sliding window.
        Current approach: Consolidate ALL facts in the collection (assuming < 1000 items works for LLM context).
        """
        try:
            # 1. Fetch All Memories
            # Limit 100 for now to fit in Context
            points, _ = self.client.scroll(
                collection_name=collection_name,
                limit=100, 
                with_payload=True,
                with_vectors=False
            )
            
            if not points:
                return

            # Prepare data for LLM
            memory_list = []
            for p in points:
                memory_list.append({
                    "id": p.id,
                    "text": p.payload.get("text"),
                    "timestamp": p.payload.get("timestamp"),
                    "score": 1.0 # Placeholder
                })
            
            # Sort by timestamp (Oldest to Newest)
            # This is CRITICAL for the LLM to know chronology
            memory_list.sort(key=lambda x: x.get("timestamp", ""))
            
            print(f"[Consolidator] retrieved {len(memory_list)} items for consolidation.")

            # 2. LLM Processing
            consolidated_facts = self._llm_consolidate(memory_list, user_name, char_name)
            
            if not consolidated_facts:
                print("[Consolidator] LLM returned empty list. Aborting to be safe.")
                return

            print(f"[Consolidator] LLM condensed to {len(consolidated_facts)} facts.")

            # 3. Update Database (Atomic-like)
            # A. Delete processed IDs
            ids_to_delete = [m["id"] for m in memory_list]
            self.client.delete(
                collection_name=collection_name,
                points_selector=models.PointIdsList(points=ids_to_delete)
            )
            print(f"[Consolidator] Deleted {len(ids_to_delete)} old records.")

            # B. Insert New Facts
            # We need to re-vectorize them. Logic needs access to Encoder.
            # Since Encoder is in LiteMemory, we should probably return results to LiteMemory 
            # or pass encoder here. Passing encoder is cleaner.
            
            # Wait, better design: Return the actions to LiteMemory to execute.
            # But LiteMemory is getting complex. Let's Pass Encoder to this class?
            # No, let's keep it simple. We will return the {new_facts, ids_to_delete} to caller.
            
            return {
                "ids_to_delete": ids_to_delete,
                "new_facts": consolidated_facts
            }

        except Exception as e:
            print(f"[Consolidator] Execution error: {e}")
            import traceback
            traceback.print_exc()
            return None

    def _llm_consolidate(self, memory_list: List[Dict], user_name: str, char_name: str) -> List[Dict]:
        """
        Call DeepSeek to consolidate facts.
        """
        prompt = f"""
You are a Memory Consolidation System.
Your goal is to clean, merge, and resolve conflicts in the provided chronologically ordered facts.

**Context:**
- User Name: "{user_name}"
- AI Name: "{char_name}"

**INPUT DATA (Oldest to Newest):**
{json.dumps([{"text": m["text"], "time": m["timestamp"]} for m in memory_list], ensure_ascii=False, indent=2)}

**INSTRUCTIONS:**
1. **Conflict Resolution**: If facts contradict (e.g., "{user_name} likes Autumn" then "{user_name} likes Summer"), KEEP THE NEWER ONE and discard the older one.
2. **De-duplication**: Merge identical or near-identical facts.
3. **Consolidation**: Combine related facts (e.g. "Likes apples", "Likes pears" -> "Likes apples and pears").
4. **Personalization**: Replace generic terms ("User", "AI", "He", "She") with specific names ("{user_name}", "{char_name}") where appropriate contextually.
5. **Output**: A simplified list of atomic facts.

**OUTPUT FORMAT**:
JSON List of strings.
Example: ["{user_name} likes Summer", "{user_name} loves coding"]
"""
        try:
            payload = {
                "model": "deepseek-chat", # Use config model ideally
                "messages": [
                    {"role": "system", "content": "You are an expert Data Consolidator."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.0 # Strict logic
            }
            
            # DEBUG LOG
            print(f"[Consolidator] [DEBUG] LLM Consolidation Prompt:\n{prompt}")
            
            response = requests.post(
                f"{self.config['openai_base_url']}/chat/completions",
                headers={"Authorization": f"Bearer {self.config['api_key']}"},
                json=payload,
                timeout=30
            ) 
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            # DEBUG LOG
            print(f"[Consolidator] [DEBUG] LLM Consolidation Output:\n{content}")
                
            facts = json.loads(content)
            return facts if isinstance(facts, list) else []
            
        except Exception as e:
            print(f"[Consolidator] LLM Error: {e}")
            return []
