"""
Dreaming System (ReM - Recursive Episodic Memory)
Handles memory extraction and consolidation for per-character isolation.
"""
import json
import os
import logging
from typing import List, Dict, Any
from datetime import datetime

# Conditional imports
try:
    from openai import OpenAI
except ImportError:
    OpenAI = None

# from llm.manager import llm_manager
from services.container import services

logger = logging.getLogger("Dreaming")


class Dreaming:
    """
    The Dreaming System (ReM - Recursive Episodic Memory).
    Cycle: Raw Logs -> Extract -> Active Memories -> (Hit) -> Pending -> Consolidate -> Active
    
    IMPORTANT: Each instance is scoped to a SINGLE character_id.
    For multi-character support, create separate instances per character.
    """
    
    def __init__(self, memory_client=None, character_id: str = "default", llm_client=None):
        """
        Initialize Dreaming for a specific character.
        Args:
            memory_client: SurrealMemory instance (shared DB connection)
            character_id: The character this dreaming instance is for (MUST be specified)
            llm_client: Optional shared OpenAI client instance
        """
        from app_config import config
        
        self.memory = memory_client
        self.character_id = character_id.lower()
        # self.api_key = config.llm.api_key  # Deprecated?
        # self.base_url = config.llm.base_url
        # self.model = config.llm.model
        self.llm_client = llm_client
        
        # 🔧 Soul Evolution Config
        self.soul_evolution_config = {
            "min_interval_minutes": 15,
            "min_memories_threshold": 20,
            "min_text_length": 500,
        }
        self._last_soul_evolution_time: datetime = None
        self._processed_memories_since_evolution: int = 0
        self._accumulated_text_for_evolution: str = ""
        
        # 🔧 External Engines
        self._soul_manager = None
        self.evolution_engine = None # Injected by Manager

    # ... (Method unchanged)

    async def process_memories(self, batch_size: int = 10):
        # ... (Start unchanged) ...
        # Consolidate
        await self._run_consolidator(limit=10)
        
        from soul_manager import SoulManager
        soul = SoulManager(self.character_id)
        
        # ⚙️ Config Constraint: Galgame imposes Evolution
        is_galgame = soul.config.get("galgame_mode_enabled", False)
        is_evolution = soul.config.get("soul_evolution_enabled", True)
        
        if is_galgame or is_evolution:
             await self._check_and_trigger_soul_evolution()
        else:
            logger.debug(f"[Dreaming] Soul Evolution DISABLED. Skipping.")

    # ... (Methods unchanged) ...

    async def _analyze_soul_evolution(self, text_batch: str):
        """
        Delegates to EvolutionEngine if available.
        """
        if self.evolution_engine:
            soul = self._get_soul_manager()
            await self.evolution_engine.analyze_and_evolve(soul, text_batch)
            return

        logger.warning("[Dreaming] EvolutionEngine not injected! Skipping evolution.")
        
    def update_llm_config(self, api_key: str, base_url: str, model: str):
        """
        Update LLM configuration dynamically.
        🔧 Refactor: Just update the local references, but LLMManager handles the actual clients.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        # We don't need to rebuild client here anymore as we fetch it on fly


    async def process_memories(self, batch_size: int = 10):
        """
        Main entry point. Runs extraction and consolidation for THIS character only.
        
        Process Flow:
        1. Extractor: Processes 'batch_size' raw logs.
        2. Consolidator: Processes pending consolidation batches via search_hybrid.
        3. Soul Evolution: Analyzes and updates personality when conditions are met.
        
        Args:
            batch_size: Number of conversation logs to process per Extractor run.
        """
        if not self.memory or not self.memory.db:
            logger.error(f"[Dreaming] No database connection for {self.character_id}")
            return
            
        logger.debug(f"[Dreaming] ✅ Starting Reverie Cycle for character '{self.character_id}'...")
        
        # Extract raw logs -> memories
        
        # [Free Tier Opt] Check Routing First
        llm_manager = services.get_llm_manager()
        route = llm_manager.get_route("dreaming")
        if route and route.provider_id == "free_tier":
            logger.info(f"[Dreaming] 🔔 Free Tier detected. Skipping extraction to save resources/prevent instability.")
            return

        await self._run_extractor(batch_size)
        
        # Consolidate frequently retrieved memories (Hit-Count Based)
        await self._run_consolidator(limit=10)
        
        from soul_manager import SoulManager
        soul = SoulManager(self.character_id)
        # 🔧 Check newly separated toggle
        if soul.config.get("soul_evolution_enabled", True): 
            await self._check_and_trigger_soul_evolution()
        else:
            logger.debug(f"[Dreaming] Soul Evolution DISABLED in settings. Skipping personality update.")

    async def reset_retry_counts(self):
        """Helper to reset stuck logs on startup (User requested 'Second Chance')"""
        try:
             # Reset logs that have failed 5+ times so they get another chance on restart
             query = "UPDATE conversation_log SET retry_count = 0 WHERE retry_count >= 5;"
             await self.memory.db.query(query)
             logger.info("[Dreaming] 🕵 Reset retry counts for stuck logs (Startup Fresh Start)")
        except Exception as e:
             logger.warning(f"[Dreaming] Failed to reset retry counts: {e}")


    # ==================== Extractor ====================
    
    async def _run_extractor(self, limit: int = 10):
        """
        conversation_log -> episodic_memory
        
        Reads raw conversation logs for THIS character only,
        extracts meaningful facts, and stores as active memories.
        """
        # 1. First check total unprocessed count
        # 🔧 Retry Filter: Only pick logs that haven't failed 5 times yet
        count_query = """
        SELECT count() FROM conversation_log 
        WHERE character_id = $character_id 
          AND is_processed = false 
          AND (retry_count IS NULL OR retry_count < 5)
        GROUP ALL;
        """
        try:
            # Bug Fix: SurrealDB async_ws might raise KeyError during violent shutdown
            count_result = await self.memory.db.query(count_query, {"character_id": self.character_id})
        except KeyError:
            logger.warning("[Dreaming] DB query interrupted during shutdown (KeyError suppression)")
            return
        except Exception as e:
            logger.warning(f"[Dreaming] Extractor query failed: {e}")
            return
        
        total_count = 0
        if count_result and isinstance(count_result, list):
            first = count_result[0]
            if isinstance(first, dict) and 'result' in first:
                 inner = first['result']
                 if inner and isinstance(inner, list) and inner and 'count' in inner[0]:
                     total_count = inner[0]['count']
            elif isinstance(first, dict) and 'count' in first:
                 total_count = first['count']
        
        # DEBUG: Print Limit and Count
        logger.info(f"[Dreaming] Extractor Check: Count={total_count}, Limit={limit}, Threshold=20")

        if total_count < 20:
             logger.debug(f"[Dreaming] Accumulating logs for {self.character_id} ({total_count}/20)...")
             return

        # 2. Fetch limit (batch_size) logs
        query = """
        SELECT * FROM conversation_log 
        WHERE character_id = $character_id 
          AND is_processed = false 
          AND (retry_count IS NULL OR retry_count < 5)
        ORDER BY created_at ASC
        LIMIT $limit;
        """
        results = await self.memory.db.query(query, {
            "character_id": self.character_id,
            "limit": limit
        })
        
        # Parse results
        logs = []
        if results and isinstance(results, list):
            first = results[0]
            if isinstance(first, dict) and 'result' in first:
                logs = first['result'] or []
            elif isinstance(first, dict):
                logs = results
            
        if not logs:
            logger.debug(f"[Dreaming] No raw logs to extract for {self.character_id}")
            return

        # DEBUG: Print IDs of fetched logs
        log_ids = [l.get('id', 'unknown') for l in logs]
        logger.info(f"[Dreaming] Extractor Fetched {len(logs)} logs: {log_ids}")

        # Prepare prompt input
        log_text = ""
        for log in logs:
            ts = log.get('created_at', '')[:16].replace('T', ' ')
            narrative = log.get('narrative', '')
            log_text += f"[{ts}] {narrative}\n"
            
        try:
            # Call LLM via Driver
            llm_manager = services.get_llm_manager()
            driver = await llm_manager.get_driver("memory")
            model_name = llm_manager.get_model_name("memory")
            
            # Use PromptManager
            from prompt_manager import prompt_manager
            
            # Load structured template
            prompt_data = prompt_manager.load_structured("extract.yaml", {"log_text": log_text})
            
            if not isinstance(prompt_data, dict):
                logger.error("[Dreaming] Failed to load structured memory extraction template")
                return

            # Construct messages
            messages = [
                {"role": "system", "content": prompt_data.get("system", "You are a memory extractor.")},
                {"role": "user", "content": prompt_data.get("user", log_text)}
            ]
            
            # DEBUG
            logger.info(f"[Extractor] Active Model: {model_name}")
            
            content = await driver.chat_completion(
                messages=messages,
                model=model_name,
                **llm_manager.get_parameters("memory")
                # response_format if driver supports it? OpenAIDriver takes kwargs.
            )
            
            content = content.strip()
            
            # === DEBUG ===
            logger.info(f"[Extractor] 📦 LLM Response received")
            logger.info(f"[Extractor] Raw response:\n{content}")
            
            # Clean markdown wrapper
            if content.startswith("```json"): 
                content = content.split("\n", 1)[1]
            if content.endswith("```"): 
                content = content.rsplit("\n", 1)[0]
            
            new_memories = json.loads(content)
            
            # Ensure it's a list
            if isinstance(new_memories, dict):
                new_memories = new_memories.get("memories", [new_memories])
            
            # Save new memories
            for item in new_memories:
                raw_text = item.get("memory", "")
                if not raw_text: continue
                
                # Generate embedding (384 dim for paraphrase-multilingual-MiniLM-L12-v2)
                vector = [0.0] * 384  # Default dimension
                if hasattr(self.memory, 'encoder') and self.memory.encoder:
                    try:
                        vector = self.memory.encoder(raw_text)
                    except Exception as e:
                        logger.warning(f"Failed to encode memory: {e}")
                
                # Store as active memory (for THIS character)
                await self.memory.add_episodic_memory(
                    character_id=self.character_id,
                    content=raw_text,
                    embedding=vector,
                    status="active"
                )
                
            # Mark logs as processed
            for log in logs:
                log_id = log.get('id', '')
                if log_id:
                    await self.memory.db.query(f"UPDATE {log_id} SET is_processed = true, retry_count = 0;")
            
            # 🔧 Accumulate processed content for Soul Evolution
            self.accumulate_for_evolution(log_text, len(new_memories))
            
            logger.info(f"[Dreaming] Extracted {len(new_memories)} fragments from {len(logs)} logs for '{self.character_id}'")
            
        except json.JSONDecodeError as e:
            logger.error(f"[Dreaming] Failed to parse LLM response as JSON: {e}")
            # 🔧 Retry Logic: Increment retry_count for this batch
            await self._handle_extraction_failure(logs)
        except Exception as e:
            logger.error(f"[Dreaming] Extractor failed for {self.character_id}: {e}")
            # 🔧 Retry Logic: Increment retry_count for this batch
            await self._handle_extraction_failure(logs)

    async def _handle_extraction_failure(self, logs: List[Dict]):
        """Helper to increment retry counts on failure"""
        try:
            for log in logs:
                log_id = log.get('id', '')
                if log_id:
                    # Increment retry_count, default to 0 if null
                    await self.memory.db.query(f"UPDATE {log_id} SET retry_count = (retry_count OR 0) + 1;")
            logger.info(f"[Dreaming] Incremented retry_count for {len(logs)} logs due to failure.")
        except Exception as db_err:
            logger.error(f"[Dreaming] Failed to update retry counts: {db_err}")


    # ==================== Consolidator ====================

    async def _run_consolidator(self, limit: int = 10):
        """
        Consolidate 'active' memories that are frequently retrieved (hit_count > 1).
        Trigger Condition: At least 20 such memories exist.
        Execution: Pick Top N (limit) by hit_count.
        """
        # 1. Check Count of candidates
        count_query = """
        SELECT count() FROM episodic_memory 
        WHERE character_id = $character_id 
          AND status = 'active'
          AND hit_count > 1
        GROUP ALL;
        """
        count_result = await self.memory.db.query(count_query, {"character_id": self.character_id})
        
        candidate_count = 0
        if count_result and isinstance(count_result, list):
             first = count_result[0]
             if isinstance(first, dict) and 'result' in first:
                 inner = first['result']
                 if inner and isinstance(inner, list) and 'count' in inner[0]:
                     candidate_count = inner[0]['count']
                     
        if candidate_count < 20:
             logger.debug(f"[Dreaming] Consolidator skipped: Only {candidate_count}/20 candidates (active & hit>1)")
             return

        logger.info(f"[Dreaming] 🧠 Consolidator Triggered! Found {candidate_count} candidates. Processing Top {limit}...")

        # 2. Fetch Top N High-Hit Memories
        query = """
        SELECT * FROM episodic_memory 
        WHERE character_id = $character_id 
          AND status = 'active' 
          AND hit_count > 1
        ORDER BY hit_count DESC
        LIMIT $limit;
        """
        results = await self.memory.db.query(query, {
            "character_id": self.character_id,
            "limit": limit
        })
        
        # Parse results
        pending_mems = []
        if results and isinstance(results, list):
            first = results[0]
            if isinstance(first, dict) and 'result' in first:
                pending_mems = first['result'] or []
            elif isinstance(first, dict):
                pending_mems = results
                
        if not pending_mems:
            return

        # Prepare LLM Input
        input_list = []
        for i, mem in enumerate(pending_mems):
            input_list.append({
                "id": str(i + 1),
                "memory": mem.get('content', ''),
                "hits": mem.get('hit_count', 0),
                "date": mem.get('created_at', '')[:10]
            })
            
        # LLM Prompt
        # Prepare LLM Input (Text blob for template)
        memory_text = json.dumps(input_list, ensure_ascii=False, indent=2)

        # Use PromptManager
        from prompt_manager import prompt_manager
        
        prompt_data = prompt_manager.load_structured("consolidate.yaml", {"memory_text": memory_text})
        
        if not isinstance(prompt_data, dict):
            logger.error("[Consolidator] Failed to load structured consolidation template")
            return

        messages = [
            {"role": "system", "content": prompt_data.get("system", "You are a memory consolidator.")},
            {"role": "user", "content": prompt_data.get("user", memory_text)}
        ]
        messages = [
            {"role": "system", "content": prompt_data.get("system", "You are a memory consolidator.")},
            {"role": "user", "content": prompt_data.get("user", memory_text)}
        ]
        try:
            # 🔧 Refactor: Use Driver
            llm_manager = services.get_llm_manager()
            driver = await llm_manager.get_driver("memory")
            model_name = llm_manager.get_model_name("memory")
            
            logger.info(f"[Consolidator] 🚀 Active Model: {model_name}")

            content = await driver.chat_completion(
                model=model_name,
                messages=messages,
                temperature=0.5
            )
            
            content = content.strip()

            # === DEBUG: Print LLM Response Content ===
            logger.info(f"[Consolidator] 📦 LLM Response received")
            logger.info(f"[Consolidator] Raw response:\n{content}")
            
            # Clean markdown
            if content.startswith("```json"): 
                content = content.split("\n", 1)[1]
            if content.endswith("```"): 
                content = content.rsplit("\n", 1)[0]
                
            consolidated_memories = json.loads(content)
            
            # Ensure list
            if isinstance(consolidated_memories, dict):
                consolidated_memories = consolidated_memories.get("memories", [consolidated_memories])

            # Save consolidated memories
            for item in consolidated_memories:
                raw_text = item.get("memory", "")
                if not raw_text: continue
                
                # Embedding
                vector = [0.0] * 384
                if hasattr(self.memory, 'encoder') and self.memory.encoder:
                    try:
                        vector = self.memory.encoder(raw_text)
                    except Exception as e:
                        logger.warning(f"Failed to encode memory: {e}")
                
                await self.memory.add_episodic_memory(
                    character_id=self.character_id,
                    content=raw_text,
                    embedding=vector,
                    # Important: New consolidated memories start fresh
                    status="active",
                    hit_count=0 
                )
            
            # Archive OLD memories
            for old_mem in pending_mems:
                mem_id = old_mem.get('id', '')
                if mem_id:
                     await self.memory.db.query(f"UPDATE {mem_id} SET status = 'archived';")
                
            logger.info(f"[Dreaming] Consolidated {len(pending_mems)} high-hit memories -> {len(consolidated_memories)} new insights")
            
        except json.JSONDecodeError as e:
            logger.error(f"[Dreaming] Failed to parse consolidator response: {e}")
        except Exception as e:
            logger.error(f"[Dreaming] Consolidator failed for {self.character_id}: {e}")

    # ==================== Soul Evolution ====================
    
    def _get_soul_manager(self):
        """Lazy load SoulManager to avoid circular imports"""
        if self._soul_manager is None:
            from soul_manager import SoulManager
            self._soul_manager = SoulManager(character_id=self.character_id)
        return self._soul_manager
    
    def accumulate_for_evolution(self, text: str, count: int = 1):
        """
        Accumulates processed text and memory count for Soul Evolution.
        Called by Extractor.
        """
        self._accumulated_text_for_evolution += text + "\n"
        self._processed_memories_since_evolution += count
    
    async def _check_and_trigger_soul_evolution(self):
        """
        Checks and triggers Soul Evolution.
        
        Conditions (Attributes must ALL be met):
        1. Time since last evolution >= min_interval_minutes
        2. Processed memories count >= min_memories_threshold
        3. Accumulated text length >= min_text_length
        """
        config = self.soul_evolution_config
        
        # Condition 1: Time Interval Check
        if self._last_soul_evolution_time:
            elapsed = (datetime.now() - self._last_soul_evolution_time).total_seconds() / 60
            if elapsed < config["min_interval_minutes"]:
                logger.debug(f"[Soul Evolution] Skipped: Only {elapsed:.1f}/{config['min_interval_minutes']} minutes since last evolution")
                return
        
        # Condition 2: Memory Count Check
        if self._processed_memories_since_evolution < config["min_memories_threshold"]:
            logger.debug(f"[Soul Evolution] Skipped: Only {self._processed_memories_since_evolution}/{config['min_memories_threshold']} memories processed")
            return
        
        # Condition 3: Text Length Check
        if len(self._accumulated_text_for_evolution) < config["min_text_length"]:
            logger.debug(f"[Soul Evolution] Skipped: Only {len(self._accumulated_text_for_evolution)}/{config['min_text_length']} chars accumulated")
            return
        
        # All conditions met, trigger evolution
        logger.info(f"[Soul Evolution] 🌸 All conditions met! Triggering evolution...")
        await self._analyze_soul_evolution(self._accumulated_text_for_evolution)
        
        # Reset Counters
        self._last_soul_evolution_time = datetime.now()
        self._processed_memories_since_evolution = 0
        self._accumulated_text_for_evolution = ""
    
    async def _analyze_soul_evolution(self, text_batch: str):
        """
        Analyzes recent memories, evolves Big Five, PAD, Traits, and Mood.
        Uses LLM JSON Output mode.
        """
        # LLM Client is now retrieved dynamically from LLMManager
        # checked later in try/catch block via get_client
        pass
        
        soul = self._get_soul_manager()
        
        # 1. Fetch random memories as context
        random_memories = []
        try:
            query = """
            SELECT content FROM episodic_memory 
            WHERE character_id = $character_id AND status = 'active'
            ORDER BY RAND() LIMIT 10;
            """
            result = await self.memory.db.query(query, {"character_id": self.character_id})
            if result and isinstance(result, list):
                first = result[0]
                if isinstance(first, dict) and 'result' in first:
                    random_memories = [m.get('content', '') for m in (first['result'] or [])]
                elif isinstance(first, dict) and 'content' in first:
                    random_memories = [m.get('content', '') for m in result]
        except Exception as e:
            logger.warning(f"[Soul Evolution] Failed to fetch random memories: {e}")
        
        random_mem_text = "\n".join([f"- {m}" for m in random_memories[:10]])
        
        # 2. Get current state
        current_traits = soul.profile.get("personality", {}).get("traits", [])
        current_big_five = soul.profile.get("personality", {}).get("big_five", {})
        current_pad = soul.profile.get("personality", {}).get("pad_model", {})
        current_mood = soul.profile.get("state", {}).get("current_mood", "neutral")
        
        # 3. Construct Prompt (Use PromptManager)
        from prompt_manager import prompt_manager
        
        context = {
            "current_traits": current_traits,
            "current_big_five": current_big_five,
            "current_pad": current_pad, 
            "current_mood": current_mood,
            "random_mem_text": random_mem_text,
            "recent_logs": text_batch[:2000] # Pass text batch for template
        }
        
        # Load structured YAML template
        # The evolve.yaml template returns {system: ..., user: ...} structure?
        # Wait, my evolve.yaml has `system: |` and `user: |`.
        # So load_structured will return a dict with those keys.
        
        prompt_data = prompt_manager.load_structured("memory/evolve.yaml", context)
        
        if not isinstance(prompt_data, dict):
            logger.error("[Soul Evolution] Failed to load structured template")
            return

        messages = [
            {"role": "system", "content": prompt_data.get("system", "You are an evolution engine.")},
            {"role": "user", "content": prompt_data.get("user", "Start evolution.")}
        ]

        try:
            logger.info(f"[Soul Evolution] 🧠 Calling LLM for Soul Evolution (JSON Mode)...")
            
            # 🔧 Refactor: Use LLMManager
            llm_manager = services.get_llm_manager()
            client = llm_manager.get_client("evolution")
            model_name = llm_manager.get_model_name("evolution")
            
            logger.info(f"[Soul Evolution] 🚀 Active Model: {model_name}")
            
            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                **llm_manager.get_parameters("evolution"),
                response_format={"type": "json_object"} if hasattr(client, 'create') else None # Loose check, mostly all support it now or ignore
            )
            
            content = response.choices[0].message.content.strip()
            logger.info(f"[Soul Evolution] Raw Response: {content[:200]}...")
            
            # Clean JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            data = json.loads(content)
            
            # Update Soul
            new_traits = data.get("new_traits")
            new_big_five = data.get("new_big_five")
            new_pad = data.get("new_pad")
            new_mood = data.get("current_mood")
            
            if new_traits and isinstance(new_traits, list):
                soul.update_traits(new_traits)
            
            if new_big_five and isinstance(new_big_five, dict):
                soul.update_big_five(new_big_five)
                
            if new_pad and isinstance(new_pad, dict):
                soul.update_pad(new_pad)
            
            if new_mood:
                soul.update_current_mood(new_mood)
            
            logger.info(f"[Soul Evolution] ✅ Evolution complete! Traits: {new_traits}, Mood: {new_mood}")
                
        except json.JSONDecodeError as e:
            logger.error(f"[Soul Evolution] Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"[Soul Evolution] Evolution analysis failed: {e}")
            import traceback
            traceback.print_exc()


# Test Stub
if __name__ == "__main__":
    import asyncio
    from memory.core import SurrealMemory
    
    async def main():
        mem = SurrealMemory(character_id="lillian")
        await mem.connect()
        
        # Create dreaming instance for specific character
        dream = Dreaming(memory_client=mem, character_id="lillian")
        await dream.process_memories()
        
        await mem.db.close()
        
    asyncio.run(main())
