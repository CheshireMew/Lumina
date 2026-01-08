import json
import time
import os
from typing import List, Dict
from lite_memory import LiteMemory
from soul_manager import SoulManager

class DreamingService:
    """
    Offline process that consolidates memory.
    1. Reads raw events from SQLite (memory_events).
    2. Extracts structured Knowledge (Graph Edges).
    3. Updates Soul State (Core Profile).
    """

    def __init__(self, base_url="http://localhost:11434/v1", api_key="ollama", memory_client: LiteMemory = None):
        
        self.base_url = base_url
        self.api_key = api_key
        
        character_id = "hiyori" # Default

        if memory_client:
            # Shared Memory Mode
            self.memory = memory_client
            character_id = getattr(memory_client, 'character_id', "hiyori")
            
            # Verify if config exists, otherwise fallback to defaults or passed args
            mem_config = getattr(memory_client, 'config', {})
            self.api_key = mem_config.get("api_key", api_key)
            self.base_url = mem_config.get("base_url", base_url)
            self.config = {
                "base_url": self.base_url,
                "api_key": self.api_key,
                "model": mem_config.get("model", "deepseek-chat")
            }
            print(f"[Dreaming] Using shared memory client for character: {character_id}")
        else:
            # Standalone mode
            print("[Dreaming] Creating new memory client (Standalone Mode).")
            # ... (config loading logic omitted for brevity, keeping existing flow but ensuring char_id is set) ...
            # Assume hiyori for standalone unless config says otherwise, logic below handles it
            
            # Try to load memory_config.json
            config_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "memory_config.json")
            loaded_config = {}
            if os.path.exists(config_path):
                try:
                    with open(config_path, 'r', encoding='utf-8') as f:
                        loaded_config = json.load(f)
                    print(f"[Dreaming] Loaded config from {config_path}")
                except Exception as e:
                    print(f"[Dreaming] Failed to load config file: {e}")

            character_id = loaded_config.get("character_id", "hiyori")
            
            # Merge defaults
            config = {
                "qdrant_path": "./lite_memory_db", 
                "sqlite_path": "./memory_db/lumina_memory.db",
                "base_url": loaded_config.get("base_url", base_url),
                "api_key": loaded_config.get("api_key", api_key),
                "embedder_model": loaded_config.get("embedder", "paraphrase-multilingual-MiniLM-L12-v2")
            }
            
            self.memory = LiteMemory(config=config, character_id=character_id)
            self.config = {
                "base_url": base_url,
                "api_key": api_key,
                "model": "deepseek-chat" 
            }
            
        # ✅ Correctly Initialize SoulManager with the right character_id
        self.soul = SoulManager(character_id=character_id)
        print(f"[Dreaming] Service initialized for '{character_id}'.")
        
    def _truncate_log(self, text, length=100):
        t = str(text).replace("\n", " ")
        return t[:length] + "..." if len(t) > length else t
        
    def wake_up(self, mode="quick"):
        """Runs one dreaming cycle (processing unprocessed events)."""
        print("\n[Dreaming] ✨ The Dreaming Process Begins... ✨")
        
        # 1. Fetch Unprocessed Events
        try:
            # Check for fetch_unprocessed_events existence (it is in TimeIndexedMemory)
            if hasattr(self.memory.sql_db, 'fetch_unprocessed_events'):
                events = self.memory.sql_db.fetch_unprocessed_events(limit=5) # Process 5 at a time
            else:
                print("[Dreaming] Error: Database does not support fetching unprocessed events.")
                return

            if not events:
                print("[Dreaming] No new unprocessed events.")
                print("[Dreaming] ⚠️ Falling back to recent history for Soul Evolution check...")
                try:
                    # Fallback: Get recent history directly
                    history = self.memory.sql_db.get_recent_chat_history(limit=5)
                    if history:
                        # Convert history dicts to event-like text
                        # History items are raw memory_events rows: event_type, content, etc.
                        fallback_text = "\n".join([f"[{h['event_type']}] {h['content']}" for h in history])
                        print(f"[Dreaming] Fallback content length: {len(fallback_text)}")
                        self._analyze_soul_evolution(fallback_text)
                except Exception as e:
                    print(f"[Dreaming] Fallback failed: {e}")
                return

            print(f"[Dreaming] 🧠 Analying {len(events)} recent memories...")
            processed_ids = []
            processed_texts = []

            for evt in events:
                text = evt.get("content", "")
                if not text:
                    processed_ids.append(evt["event_id"])
                    continue
                    
                print(f"[Dreaming] Dreaming of: '{self._truncate_log(text)}'")
                processed_texts.append(text)
                
                # 2. Extract Triples (LLM) - DISABLED
                # triples = self._extract_triples(text)
                triples = []
                
                # 3. Write to Knowledge Graph
                # if triples:
                #     print(f"  > 🕸️ Woven {len(triples)} connections.")
                #     for src, rel, tgt in triples:
                #         self.memory.add_knowledge_edge(src, tgt, rel)
                # else:
                #     print("  > No new connections found.")
                
                # 4. Deep Reflection (Soul Update)
                # Apply simple heuristic logic to REAL text
                if "stress" in text.lower() or "fail" in text.lower() or "sad" in text.lower():
                     self.soul.mutate_mood(d_p=-0.05, d_a=0.1)
                elif "relax" in text.lower() or "happy" in text.lower() or "love" in text.lower():
                     self.soul.mutate_mood(d_p=0.05, d_a=-0.1)

                processed_ids.append(evt["event_id"])

            # 5. Mark Processed
            # 5. Soul Evolution (Traits & Obsession)
            if processed_texts:
                full_text = "\n".join(processed_texts)
                self._analyze_soul_evolution(full_text)

            # 6. Mark Processed
            self.memory.sql_db.mark_events_processed(processed_ids)
            print(f"[Dreaming] ✨ Dream Cycle Complete. Digested {len(processed_ids)} memories.")
            
        except Exception as e:
            print(f"[Dreaming] Critical Error in Dream Cycle: {e}")
            import traceback
            traceback.print_exc()

    def _extract_triples(self, text: str) -> List[tuple]:
        """
        Uses LLM to extract (Subject, Relation, Object) triples from text.
        """
        import requests
        
        prompt = f"""
        Extract a Knowledge Graph from the following text.
        Return a JSON list of triples: [["Subject", "RELATION", "Object"], ...].
        
        Rules:
        1. "Subject" and "Object" should be entities (Person, Concept, Place).
        2. "RELATION" must be UPPERCASE (e.g., LIKES, VISITED, IS_STRESSED_BY).
        3. Keep it concise.
        4. If the user is mentioned, use "User".
        5. Facts only.
        
        Text: "{text}"
        
        JSON Output:
        """
        
        try:
            # Check for Environment Variables Override
            env_base_url = os.environ.get("OPENAI_BASE_URL")
            env_api_key = os.environ.get("OPENAI_API_KEY")
            
            # Priority: Env Var > Config (支持 base_url 和 openai_base_url 两种字段名)
            base_url = env_base_url or self.memory.config.get("base_url") or self.memory.config.get("openai_base_url", "http://localhost:11434/v1")
            api_key = env_api_key or self.memory.config.get("api_key", "ollama")
            
            # 获取角色名
            char_name = self.soul.profile.get("identity", {}).get("name", "Hiyori")
            
            # Define Payload BEFORE using it
            payload = {
                "model": "deepseek-chat", # Or use self.memory.config model
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a Knowledge Graph Creator. Output JSON only."},
                    {"role": "user", "name": char_name, "content": prompt}  # 使用角色名
                ],
                "stream": False,
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            
            # Log LLM interaction
            text_preview = text[:100].replace('\n', ' ') + '...' if len(text) > 100 else text.replace('\n', ' ')
            print(f"[Dreaming] 调用 LLM 提取知识图谱: {text_preview}")
            print(f"[Dreaming] Connecting to LLM at: {base_url} (Model: {payload['model']})...")
            
            response = requests.post(f"{base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=90)
            response.raise_for_status()
            
            content = response.json()['choices'][0]['message']['content']
            content_preview = content[:100].replace('\n', ' ') + '...' if len(content) > 100 else content.replace('\n', ' ')
            print(f"[Dreaming] LLM 返回: {content_preview}")
            
            # Simple parsing of potential JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            
            # Handle both {"triples": [[...]]} and [[...]] formats
            if isinstance(data, dict):
                # Try to find a list value
                for k, v in data.items():
                    if isinstance(v, list):
                        return v
                return []
            elif isinstance(data, list):
                return data
            return []
            
        except requests.exceptions.ConnectionError:
            print(f"[Dreaming] ❌ Connection Failed: Could not connect to LLM at {base_url}.")
            print(f"[Dreaming] ℹ️ Hint: Ensure Ollama is running (`ollama serve`) or set correct OPENAI_BASE_URL.")
            print(f"[Dreaming] ⚠️ Falling back to MOCK data to verify Graph Writing logic.")
            return [("User", "FAILED_TO_CONNECT", "LLM"), ("System", "USED", "Fallback_Mock")]
            
        except Exception as e:
            print(f"[Dreaming] ⚠️ Extraction Failed: {e}")
            return []

    def _analyze_soul_evolution(self, text_batch: str):
        """
        Analyzes recent memories AND random past memories to evolve traits, big_five, and pad_model.
        Uses DeepSeek JSON Output mode.
        """
        if not text_batch or len(text_batch) < 50: return

        print(f"\n[Dreaming] 🌱 Reflecting on Soul Evolution...")
        
        # 1. Fetch Random Memories for context
        random_memories = self.memory.get_random_inspiration(limit=10)
        random_mem_text = "\n".join([f"- {m['content']} (Emotion: {m['emotion']})" for m in random_memories])

        # 2. Prepare Current State
        current_traits = self.soul.profile.get("personality", {}).get("traits", [])
        current_big_five = self.soul.profile.get("personality", {}).get("big_five", {})
        current_pad = self.soul.profile.get("personality", {}).get("pad_model", {})
        current_mood = self.soul.profile.get("state", {}).get("current_mood", "neutral")
        
        # 3. Construct Prompt
        system_prompt = """
You are a master-level psychology expert. Your goal is to evolve the internal state of a human based on their recent experiences and past memories.

You must output a valid JSON object strictly following the structure below.
Here is:
1. Current Personality State (Big Five, PAD, Traits, Current Mood)
2. Recent Interactions (What just happened)
3. Random Past Memories (Context/Long-term patterns)

Your Task:
Analyze the Recent Interactions in the context of the character's history.
Determine how the character's internal state should shift.
Output the NEW ABSOLUTE VALUES for Big Five and PAD, and a potentially updated list of Traits.
Also select the most appropriate "current_mood" tag from the allowed list: 
[happy], [sad], [angry], [neutral], [tired], [excited], [shy], [obsessed], [confused]

EXAMPLE JSON OUTPUT:
{
    "new_traits": ["<derive 4-5 traits from interaction>"],
    "new_big_five": {
        "openness": <choose number between 0.0 and 1.0>,
        "conscientiousness": <choose number between 0.0 and 1.0>,
        "extraversion": <choose number between 0.0 and 1.0>,
        "agreeableness": <choose number between 0.0 and 1.0>,
        "neuroticism": <choose number between 0.0 and 1.0>
    },
    "new_pad": {
        "pleasure": <choose number between 0.0 and 1.0>,
        "arousal": <choose number between 0.0 and 1.0>,
        "dominance": <choose number between 0.0 and 1.0>
    },
    "current_mood":  (choose from: [happy], [sad], [angry], [neutral], [tired], [excited], [shy], [obsessed], [confused])
}
"""

        user_prompt = f"""
Random Past Memories (Context):
{random_mem_text}

Recent Interactions (Focus on this):
"{text_batch[:2000]}"

Instruction:
Based on the interactions, output the NEW state. 
- **Big Five and PAD values must be specific floats between 0.0 and 1.0.**
- **Do NOT simply copy the Current State.** You must decide if the recent interaction implies a change (increase or decrease).
- If the interaction is neutral, small changes are fine. If emotional, larger shifts are expected.
- Determine if 'Traits' need to change (keep 4-5 adjectives).
- Select a 'current_mood' from the allowed list.
- **You MUST return ALL fields (new_big_five, new_pad, current_mood) in the JSON.**
- Return valid JSON only.
"""
        
        try:
             # Reuse extraction logic configuration
             env_base_url = os.environ.get("OPENAI_BASE_URL")
             env_api_key = os.environ.get("OPENAI_API_KEY")
             
             # Priority: Env Var > self.memory.config > Default
             # Note: self.memory.config is populated from memory_config.json in standalone mode
             base_url = env_base_url or self.memory.config.get("base_url") or "http://localhost:11434/v1"
             api_key = env_api_key or self.memory.config.get("api_key") or "ollama"
             
             payload = {
                "model": self.memory.config.get("model", "deepseek-chat"),
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "stream": False,
                "temperature": 0.4, # Slightly higher temp to encourage change
                "response_format": {"type": "json_object"}
            }
             
             import requests
             print(f"[Dreaming] 🧠 Calling LLM for Soul Evolution (JSON Mode)...")
             response = requests.post(f"{base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {api_key}"}, timeout=60)
             response.raise_for_status()
             
             content = response.json()['choices'][0]['message']['content']
             print(f"[Dreaming] Raw Response: {content[:100]}...")
             
             # Robust JSON Parsing
             if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
             elif "```" in content:
                content = content.split("```")[1].strip()
            
             data = json.loads(content)
             
             # Extract and Update
             new_traits = data.get("new_traits")
             new_big_five = data.get("new_big_five")
             new_pad = data.get("new_pad")
             new_mood = data.get("current_mood")
             
             if new_traits and isinstance(new_traits, list):
                 self.soul.update_traits(new_traits)
             
             if new_big_five and isinstance(new_big_five, dict):
                 self.soul.update_big_five(new_big_five)
                 
             if new_pad and isinstance(new_pad, dict):
                 self.soul.update_pad(new_pad)
            
             if new_mood:
                 self.soul.update_current_mood(new_mood)
                 
        except Exception as e:
            print(f"[Dreaming] ⚠️ Evolution Analysis Failed: {e}")
            import traceback
            traceback.print_exc()


if __name__ == "__main__":
    dreamer = DreamingService()
    dreamer.wake_up()
