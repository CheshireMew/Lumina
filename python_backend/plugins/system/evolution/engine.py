import json
import logging
from typing import Dict, Any, List

logger = logging.getLogger("EvolutionEngine")

class EvolutionEngine:
    """
    Soul Evolution Engine.
    Handles the "Biological Evolution" of the digital soul based on memories.
    Driven by `prompts/memory/evolve.yaml`.
    """

    def __init__(self, context):
        self.context = context
        # We access LLMManager via context's exposed property
        self.llm_manager = context.llm_manager

    async def fetch_recent_logs(self, character_id: str, minutes: int = 1440) -> str:
        """Fetch conversation logs from the last X minutes."""
        memory_client = self.context.memory
        if not memory_client: return ""
        
        try:
            db = await memory_client.connect()
            # SurrealQL: time::now() - 24h
            query = f"""
            SELECT content, role, created_at FROM conversation_log 
            WHERE character_id = $cid 
            AND created_at > time::now() - {minutes}m
            ORDER BY created_at ASC;
            """
            result = await db.query(query, {"cid": character_id})
            
            logs = []
            if result and isinstance(result, list):
                first = result[0]
                if isinstance(first, dict) and 'result' in first:
                    rows = first['result'] or []
                    for r in rows:
                        role = r.get("role", "unknown")
                        txt = r.get("content", "")
                        logs.append(f"{role}: {txt}")
                elif isinstance(first, dict): # Single result
                     pass # handled generically
            
            return "\n".join(logs)
        except Exception as e:
            logger.error(f"[Evolution] Log fetch failed: {e}")
            return ""

    async def analyze_and_evolve(self, soul_manager, text_batch: str = None):
        """
        Analyzes recent memories/text and evolves the Soul's personality.
        Args:
            soul_manager: The active SoulManager instance.
            text_batch: Accumulated text to analyze. If None, fetches from DB.
        """
        if text_batch is None:
            text_batch = await self.fetch_recent_logs(soul_manager.character_id)
            
        if not text_batch:
            logger.info("[Evolution] No recent logs to analyze.")
            return

        if not self.llm_manager:
            logger.error("[Evolution] LLMManager not found. Cannot evolve.")
            return

        character_id = soul_manager.character_id
        
        # 1. Fetch Random Memories for Context
        random_mem_text = await self._fetch_random_memories(character_id, soul_manager)
        
        # 2. Get Current State
        profile = soul_manager.profile
        context = {
            "current_traits": profile.get("personality", {}).get("traits", []),
            "current_big_five": profile.get("personality", {}).get("big_five", {}),
            "current_pad": profile.get("personality", {}).get("pad_model", {}),
            "current_mood": profile.get("state", {}).get("current_mood", "neutral"),
            "random_mem_text": random_mem_text,
            "recent_logs": text_batch[:2500] # Cap size
        }
        
        # 3. Load Prompt
        from prompt_manager import prompt_manager
        prompt_data = prompt_manager.load_structured("evolve.yaml", context)
        
        if not isinstance(prompt_data, dict):
            logger.error("[Evolution] Failed to load evolve.yaml")
            return

        messages = [
            {"role": "system", "content": prompt_data.get("system", "You are an evolution engine.")},
            {"role": "user", "content": prompt_data.get("user", "Start evolution.")}
        ]
        
        # 4. Call LLM
        # 4. Call LLM
        try:
            logger.info(f"[Evolution] 馃 Evolving Soul for {character_id}...")
            
            # Use High-Level Driver API (Simplified)
            driver = await self.llm_manager.get_driver("evolution")
            model_name = self.llm_manager.get_model_name("evolution")
            params = self.llm_manager.get_parameters("evolution")
            
            # Since BaseLLMDriver.chat_completion returns string/content directly for stream=False
            content = await driver.chat_completion(
                messages=messages,
                model=model_name,
                **params,
                # extra kwargs
                response_format={"type": "json_object"}
            )
            
            # Just clean
            content = content.strip()
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
                
            data = json.loads(content)
            
            # 5. Apply Updates
            self._apply_updates(soul_manager, data)
            
            logger.info(f"[Evolution] 鉁?Evolution Complete for {character_id}")
            
        except Exception as e:
            logger.error(f"[Evolution] Failed: {e}")
            import traceback
            traceback.print_exc()

    async def consolidate_memories(self, soul_manager) -> bool:
        """
        Consolidate daily memories into a summary.
        """
        if not self.llm_manager:
            return False
            
        memory_client = self.context.memory
        if not memory_client:
            return False
            
        character_id = soul_manager.character_id
        logger.info(f"[Evolution] 馃Ч Consolidating memories for {character_id}...")
        
        try:
            # 1. Fetch recent memories
            # We use direct DB query since Driver is Surreal-specific here
            db = await memory_client.connect()
            query = """
            SELECT content FROM episodic_memory 
            WHERE character_id = $cid 
            AND type != 'summary'
            ORDER BY created_at DESC LIMIT 50;
            """
            result = await db.query(query, {"cid": character_id})
            
            # Parse result
            mems = []
            if result and isinstance(result, list):
                first = result[0]
                if isinstance(first, dict) and 'result' in first:
                    mems = [m.get('content', '') for m in (first['result'] or [])]
                elif isinstance(first, dict): # Single dict result?
                     mems = [m.get('content', '') for m in result]
            
            if not mems:
                logger.info("[Evolution] No memories to consolidate.")
                return False
                
            text_block = "\n".join(mems)
            
            # 2. Summarize
            prompt = f"""
            Summarize the following user-AI interactions into a concise narrative for long-term memory.
            Focus on key facts, user preferences, and important events. Ignore trivial chit-chat.
            
            Interactions:
            {text_block}
            
            Summary:
            """
            
            driver = await self.llm_manager.get_driver("chat")
            model = self.llm_manager.get_model_name("chat")
            
            summary = await driver.chat_completion(
                messages=[{"role": "user", "content": prompt}],
                model=model
            )
            
            if not summary:
                return False
                
            # 3. Store Summary
            # We store it as a special memory type 'summary'
            await memory_client.create("episodic_memory", {
                "character_id": character_id,
                "content": f"[Daily Summary] {summary}",
                "type": "summary",
                "created_at": "time::now()",
                "status": "active"
                # TODO: Generate embedding if possible, but for now text is enough
            })
            
            logger.info(f"[Evolution] 鉁?Memory Consolidated: {summary[:50]}...")
            return True
            
        except Exception as e:
            logger.error(f"[Evolution] Consolidation failed: {e}")
            return False

    async def _fetch_random_memories(self, character_id: str, soul_manager) -> str:
        """Fetch random memories from DB"""
        memory_client = self.context.memory
        if not memory_client:
            return ""
            
        try:
            db = await memory_client.connect()
            query = """
            SELECT content FROM episodic_memory 
            WHERE character_id = $character_id AND status = 'active'
            ORDER BY rand() LIMIT 10;
            """
            result = await db.query(query, {"character_id": character_id})
            
            mems = []
            if result and isinstance(result, list):
                # Surreal wrapper handling
                first = result[0]
                if isinstance(first, dict) and 'result' in first:
                    mems = [m.get('content', '') for m in (first['result'] or [])]
                elif isinstance(first, dict):
                     mems = [m.get('content', '') for m in result]
            
            return "\n".join([f"- {m}" for m in mems])
        except Exception as e:
            logger.warning(f"[Evolution] DB Fetch failed: {e}")
            return ""

    def _apply_updates(self, soul, data: Dict):
        """Apply changes to soul"""
        updates = []
        
        if "new_traits" in data:
            soul.update_traits(data["new_traits"])
            updates.append("Traits")
            
        if "new_big_five" in data:
            soul.update_big_five(data["new_big_five"])
            updates.append("Big5")
            
        if "new_pad" in data:
            soul.update_pad(data["new_pad"])
            updates.append("PAD")
            
        if "current_mood" in data:
            soul.update_current_mood(data["current_mood"])
            updates.append("Mood")
            
        if updates:
            logger.info(f"[Evolution] Updated: {', '.join(updates)}")
