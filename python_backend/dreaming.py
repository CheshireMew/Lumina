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

from llm.manager import llm_manager

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
        self.character_id = character_id.lower()  # Normalize for consistency
        
        # LLM Config from centralized config
        # LLM Config from centralized config
        # ⚡ Deprecated: Now using LLMManager logic, these are just for reference or fallback
        self.api_key = config.llm.api_key 
        self.base_url = config.llm.base_url
        self.model = config.llm.model
        
        # Initialize LLM client (Shared or New)
        # ⚡ Refactor: We no longer store a persistent client here if we want dynamic routing.
        # But for backward compatibility with passed-in clients (if any), we keep it.
        # However, we prefer using llm_manager.get_client() on demand.
        self.llm_client = llm_client
        
        # ⚡ Soul Evolution 配置
        self.soul_evolution_config = {
            "min_interval_minutes": 15,       # 两次演化间隔至少 15 分钟
            "min_memories_threshold": 20,     # 至少处理 20 条新记忆后触发
            "min_text_length": 500,           # 分析文本至少 500 字符
        }
        self._last_soul_evolution_time: datetime = None
        self._processed_memories_since_evolution: int = 0
        self._accumulated_text_for_evolution: str = ""
        
        # ⚡ Soul Manager (延迟加载，避免循环导入)
        self._soul_manager = None
        
    def update_llm_config(self, api_key: str, base_url: str, model: str):
        """
        Update LLM configuration dynamically.
        ⚡ Refactor: Just update the local references, but LLMManager handles the actual clients.
        """
        self.api_key = api_key
        self.base_url = base_url
        self.model = model
        # We don't need to rebuild client here anymore as we fetch it on fly


    async def process_memories(self, batch_size: int = 10):
        """
        Main entry point. Runs extraction and consolidation for THIS character only.
        
        流程:
        1. Extractor: 处理 batch_size 条未处理的对话日志
        2. Consolidator: 处理 BatchManager 中的待整合批次（由 search_hybrid 创建）
        3. Soul Evolution: 满足条件时分析并更新性格
        
        Args:
            batch_size: Extractor 每次处理的对话日志条数
        """
        if not self.memory or not self.memory.db:
            logger.error(f"[Dreaming] No database connection for {self.character_id}")
            return
            
        logger.debug(f"[Dreaming] ✨ Starting Reverie Cycle for character '{self.character_id}'...")
        
        # Phase 1: Extract raw logs -> memories
        
        # [Free Tier Opt] Check Routing First
        route = llm_manager.get_route("dreaming")
        if route and route.provider_id == "free_tier":
            logger.info(f"[Dreaming] ⏸️ Free Tier detected. Skipping extraction to save resources/prevent instability.")
            return

        await self._run_extractor(batch_size)
        
        # Phase 2: Consolidate frequently retrieved memories (Hit-Count Based)
        await self._run_consolidator(limit=10)
        
        from soul_manager import SoulManager
        soul = SoulManager(self.character_id)
        # ⚡ Check newly separated toggle
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
             logger.info("[Dreaming] 🔄 Reset retry counts for stuck logs (Startup Fresh Start)")
        except Exception as e:
             logger.warning(f"[Dreaming] Failed to reset retry counts: {e}")


    # ==================== Phase 1: Extractor ====================
    
    async def _run_extractor(self, limit: int = 10):
        """
        Phase 1: conversation_log -> episodic_memory
        
        Reads raw conversation logs for THIS character only,
        extracts meaningful facts, and stores as active memories.
        """
        # 1. First check total unprocessed count
        # ⚡ Retry Filter: Only pick logs that haven't failed 5 times yet
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
            # Call LLM
            # ⚡ Refactor: Use LLMManager
            client = llm_manager.get_client("memory")
            model_name = llm_manager.get_model_name("memory")
            
            # Use PromptManager
            from prompt_manager import prompt_manager
            
            # Load structured template which returns a dict: {"system": "...", "user": "..."}
            prompt_data = prompt_manager.load_structured("memory/extract.yaml", {"log_text": log_text})
            
            if not isinstance(prompt_data, dict):
                logger.error("[Dreaming] Failed to load structured memory extraction template")
                return

            # Construct messages
            messages = [
                {"role": "system", "content": prompt_data.get("system", "You are a memory extractor.")},
                {"role": "user", "content": prompt_data.get("user", log_text)}
            ]
            
            # === DEBUG: 打印发送给 LLM 的内容 (Summarized) ===
            logger.info(f"[Extractor] Active Model: {model_name}")
            logger.info(f"[Extractor] Sending to LLM ({len(logs)} logs) via {model_name}")

            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                **llm_manager.get_parameters("memory")
            )

            
            content = response.choices[0].message.content.strip()
            
            # === DEBUG: 打印 LLM 返回的内容 ===
            logger.info(f"[Extractor] 📥 LLM Response received")
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
            
            # ⚡ 累积处理的内容，供 Soul Evolution 使用
            self.accumulate_for_evolution(log_text, len(new_memories))
            
            logger.info(f"[Dreaming] Extracted {len(new_memories)} fragments from {len(logs)} logs for '{self.character_id}'")
            
        except json.JSONDecodeError as e:
            logger.error(f"[Dreaming] Failed to parse LLM response as JSON: {e}")
            # ⚡ Retry Logic: Increment retry_count for this batch
            await self._handle_extraction_failure(logs)
        except Exception as e:
            logger.error(f"[Dreaming] Extractor failed for {self.character_id}: {e}")
            # ⚡ Retry Logic: Increment retry_count for this batch
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


    # ==================== Phase 2: Consolidator ====================

    async def _run_consolidator(self, limit: int = 10):
        """
        Phase 2: Consolidate 'active' memories that are frequently retrieved (hit_count > 1).
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

        # 准备 LLM 输入
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
        
        prompt_data = prompt_manager.load_structured("memory/consolidate.yaml", {"memory_text": memory_text})
        
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
            # ⚡ Refactor: Use LLMManager
            client = llm_manager.get_client("memory")
            model_name = llm_manager.get_model_name("memory")
            
            logger.info(f"[Consolidator] 🚀 Active Model: {model_name}")

            response = await client.chat.completions.create(
                model=model_name,
                messages=messages,
                temperature=0.5
            )
            
            content = response.choices[0].message.content.strip()

            # === DEBUG: 打印 LLM 返回的内容 ===
            logger.info(f"[Consolidator] 📥 LLM Response received")
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

    # ==================== Phase 3: Soul Evolution ====================
    
    def _get_soul_manager(self):
        """延迟加载 SoulManager，避免循环导入"""
        if self._soul_manager is None:
            from soul_manager import SoulManager
            self._soul_manager = SoulManager(character_id=self.character_id)
        return self._soul_manager
    
    def accumulate_for_evolution(self, text: str, count: int = 1):
        """
        累积处理的文本和记忆数量，供 Soul Evolution 使用。
        由 Extractor 调用。
        """
        self._accumulated_text_for_evolution += text + "\n"
        self._processed_memories_since_evolution += count
    
    async def _check_and_trigger_soul_evolution(self):
        """
        检查并触发 Soul Evolution。
        
        触发条件（需全部满足）：
        1. 距离上次演化 >= min_interval_minutes 分钟
        2. 累计处理 >= min_memories_threshold 条记忆
        3. 累计文本长度 >= min_text_length 字符
        """
        config = self.soul_evolution_config
        
        # 条件1: 时间间隔检查
        if self._last_soul_evolution_time:
            elapsed = (datetime.now() - self._last_soul_evolution_time).total_seconds() / 60
            if elapsed < config["min_interval_minutes"]:
                logger.debug(f"[Soul Evolution] Skipped: Only {elapsed:.1f}/{config['min_interval_minutes']} minutes since last evolution")
                return
        
        # 条件2: 记忆数量检查
        if self._processed_memories_since_evolution < config["min_memories_threshold"]:
            logger.debug(f"[Soul Evolution] Skipped: Only {self._processed_memories_since_evolution}/{config['min_memories_threshold']} memories processed")
            return
        
        # 条件3: 文本长度检查
        if len(self._accumulated_text_for_evolution) < config["min_text_length"]:
            logger.debug(f"[Soul Evolution] Skipped: Only {len(self._accumulated_text_for_evolution)}/{config['min_text_length']} chars accumulated")
            return
        
        # 所有条件满足，触发演化
        logger.info(f"[Soul Evolution] 🌱 All conditions met! Triggering evolution...")
        await self._analyze_soul_evolution(self._accumulated_text_for_evolution)
        
        # 重置计数器
        self._last_soul_evolution_time = datetime.now()
        self._processed_memories_since_evolution = 0
        self._accumulated_text_for_evolution = ""
    
    async def _analyze_soul_evolution(self, text_batch: str):
        """
        分析最近的记忆，演化 Big Five、PAD、Traits 和 Mood。
        使用 LLM JSON Output 模式。
        """
        # LLM Client is now retrieved dynamically from LLMManager
        # checked later in try/catch block via get_client
        pass
        
        soul = self._get_soul_manager()
        
        # 1. 获取随机记忆作为上下文
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
        
        # 2. 获取当前状态
        current_traits = soul.profile.get("personality", {}).get("traits", [])
        current_big_five = soul.profile.get("personality", {}).get("big_five", {})
        current_pad = soul.profile.get("personality", {}).get("pad_model", {})
        current_mood = soul.profile.get("state", {}).get("current_mood", "neutral")
        
        # 3. 构建 Prompt (Use PromptManager)
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
            
            # ⚡ Refactor: Use LLMManager
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
            
            # 清理 JSON
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            data = json.loads(content)
            
            # 更新 Soul
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
            
            logger.info(f"[Soul Evolution] ✨ Evolution complete! Traits: {new_traits}, Mood: {new_mood}")
                
        except json.JSONDecodeError as e:
            logger.error(f"[Soul Evolution] Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"[Soul Evolution] Evolution analysis failed: {e}")
            import traceback
            traceback.print_exc()


# Test Stub
if __name__ == "__main__":
    import asyncio
    from surreal_memory import SurrealMemory
    
    async def main():
        mem = SurrealMemory(character_id="lillian")
        await mem.connect()
        
        # Create dreaming instance for specific character
        dream = Dreaming(memory_client=mem, character_id="lillian")
        await dream.process_memories()
        
        await mem.db.close()
        
    asyncio.run(main())
