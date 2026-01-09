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

logger = logging.getLogger("Dreaming")


class Dreaming:
    """
    The Dreaming System (ReM - Recursive Episodic Memory).
    Cycle: Raw Logs -> Extract -> Active Memories -> (Hit) -> Pending -> Consolidate -> Active
    
    IMPORTANT: Each instance is scoped to a SINGLE character_id.
    For multi-character support, create separate instances per character.
    """
    
    def __init__(self, memory_client=None, character_id: str = "default"):
        """
        Initialize Dreaming for a specific character.
        
        Args:
            memory_client: SurrealMemory instance (shared DB connection)
            character_id: The character this dreaming instance is for (MUST be specified)
        """
        self.memory = memory_client
        self.character_id = character_id.lower()  # Normalize for consistency
        
        # LLM Config
        self.api_key = os.environ.get("OPENAI_API_KEY", "")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")
        
        # Load config overrides
        self._load_config()
        
        # Initialize LLM client
        self.llm_client = None
        if OpenAI and self.api_key:
            self.llm_client = OpenAI(api_key=self.api_key, base_url=self.base_url)
        
        # ⚡ Soul Evolution 配置
        self.soul_evolution_config = {
            "min_interval_minutes": 30,       # 两次演化间隔至少 30 分钟
            "min_memories_threshold": 20,     # 至少处理 20 条新记忆后触发
            "min_text_length": 500,           # 分析文本至少 500 字符
        }
        self._last_soul_evolution_time: datetime = None
        self._processed_memories_since_evolution: int = 0
        self._accumulated_text_for_evolution: str = ""
        
        # ⚡ Soul Manager (延迟加载，避免循环导入)
        self._soul_manager = None
        
        logger.info(f"[Dreaming] Initialized for character: {self.character_id}")

    def _load_config(self):
        """Load LLM config from memory_config.json if available."""
        # Use absolute path based on file location
        base_dir = os.path.dirname(os.path.abspath(__file__))
        config_path = os.path.join(base_dir, "memory_config.json")
        
        if os.path.exists(config_path):
            try:
                with open(config_path, "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if config.get("base_url"): self.base_url = config["base_url"]
                    if config.get("api_key"): self.api_key = config["api_key"]
                    if config.get("model"): self.model = config["model"]
            except Exception as e:
                logger.warning(f"Failed to load memory_config.json at {config_path}: {e}")


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
        await self._run_extractor(limit=batch_size)
        
        # Phase 2: Consolidate frequently retrieved memories (Hit-Count Based)
        await self._run_consolidator(limit=10)
        
        # Phase 3: Soul Evolution (条件触发)
        await self._check_and_trigger_soul_evolution()


    # ==================== Phase 1: Extractor ====================
    
    async def _run_extractor(self, limit: int = 10):
        """
        Phase 1: conversation_log -> episodic_memory
        
        Reads raw conversation logs for THIS character only,
        extracts meaningful facts, and stores as active memories.
        """
        # 1. First check total unprocessed count
        count_query = """
        SELECT count() FROM conversation_log 
        WHERE character_id = $character_id 
          AND is_processed = false GROUP ALL;
        """
        count_result = await self.memory.db.query(count_query, {"character_id": self.character_id})
        
        total_count = 0
        if count_result and isinstance(count_result, list):
            first = count_result[0]
            if isinstance(first, dict) and 'result' in first:
                 # result might be [{'count': 25}]
                 inner = first['result']
                 if inner and isinstance(inner, list) and inner and 'count' in inner[0]:
                     total_count = inner[0]['count']
            elif isinstance(first, dict) and 'count' in first:
                 # Direct format: [{'count': 45}]
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
            
        # LLM Prompt
        prompt = f"""你是核心记忆提取模块。

### 任务：
从对话日志中提取有价值的事实，并进行发散联想。
注意：
1. 对话日志是由语音转录生成的，因此可能存在错别字或谐音字以及无意义的错乱文字，请进行修正。
2. 重复或冲突的事实请根据上下文自动合并，同时将所有可以合并的对话合并成一条事实
3. 同时每句对话中可能包含多个不同的主体和事实，请把它分离成多个"memory"片段

### 输出格式 (必须是标准的 JSON List):
[ 
  {{"memory": "[日期+时间] [主体1+事实][对记忆简短的发散联想]"}},
  {{"memory": "[日期+时间] [主体1+事实][对记忆简短的发散联想]"}},
  {{"memory": "[日期+时间] [主体2+事实][对记忆简短的发散联想]"}},
  {{"memory": "[日期+时间] [主体3+事实][对记忆简短的发散联想]"}},
]
注意：必须是JSON格式列表。

[Raw Logs]:
{log_text}
"""
        
        try:
            # Call LLM
            if not self.llm_client:
                logger.warning(f"[Dreaming] No LLM client configured, skipping extraction")
                return
            
            # === DEBUG: 打印发送给 LLM 的内容 ===
            logger.info(f"[Extractor] 📤 Sending to LLM ({len(logs)} logs):")
            logger.info(f"[Extractor] Prompt:\n{prompt}")
                
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a memory extractor. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3
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
                    await self.memory.db.query(f"UPDATE {log_id} SET is_processed = true;")
            
            # ⚡ 累积处理的内容，供 Soul Evolution 使用
            self.accumulate_for_evolution(log_text, len(new_memories))
            
            logger.info(f"[Dreaming] Extracted {len(new_memories)} fragments from {len(logs)} logs for '{self.character_id}'")
            
        except json.JSONDecodeError as e:
            logger.error(f"[Dreaming] Failed to parse LLM response as JSON: {e}")
        except Exception as e:
            logger.error(f"[Dreaming] Extractor failed for {self.character_id}: {e}")


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
        prompt = f"""你是记忆重构架构师。

### 输入数据（这些是经常被回忆起的高频记忆，说明它们很重要）：
{json.dumps(input_list, ensure_ascii=False, indent=2)}
注意：对话日志是由语音转录生成的，因此可能存在错别字或谐音字以及无意义的错乱文字，请进行修正。

### 处理逻辑：
- 提炼：这些记忆被反复提及，请提取其中最核心、最持久的信息。
- 升华：将具体的事件转化为深刻理解（如性格特质、偏好、潜在意识
- 去重：如果多条记忆重复，请合并为一条。
- 矛盾：修正过时信息。
- 句对话中可能包含多个不同的主体和事实，请把它分离成多个"memory"片段

### 输出格式 (仅 JSON 列表):
[
  {{"memory": "[日期+时间] [主体1+事实][基于高频回忆的简短深刻洞察]"}},
  {{"memory": "[日期+时间] [主体1+事实][基于高频回忆的简短深刻洞察]"}},
  {{"memory": "[日期+时间] [主体2+事实][基于高频回忆的简短深刻洞察]"}},
  {{"memory": "[日期+时间] [主体3+事实][基于高频回忆的简短深刻洞察]"}},
]
注意：必须是JSON格式列表。不要输出其他内容。
"""
        
        try:
            if not self.llm_client:
                logger.warning("[Dreaming] LLM client not available for consolidator")
                return

            # === DEBUG: 打印发送给 LLM 的内容 ===
            logger.info(f"[Consolidator] 📤 Sending to LLM ({len(pending_mems)} memories):")
            logger.info(f"[Consolidator] Prompt:\n{prompt}")

            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a memory consolidator. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
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


    async def _run_consolidator_with_batch(self, batch):
        """
        使用 BatchManager 批次处理 Consolidator
        
        处理指定批次中的记忆（由 search_hybrid 检索创建）
        这些记忆语义相关，应该一起整合
        
        Args:
            batch: ConsolidationBatch 对象
        """
        from consolidation_batch import ConsolidationBatch
        
        if not isinstance(batch, ConsolidationBatch):
            logger.error("[Dreaming] Invalid batch type")
            return
            
        memory_ids = batch.retrieved_ids
        if not memory_ids:
            logger.debug(f"[Dreaming] Batch {batch.batch_id} has no memories")
            return
        
        # 根据 ID 查询记忆内容
        pending_mems = []
        for mem_id in memory_ids:
            try:
                result = await self.memory.db.query(f"SELECT * FROM {mem_id}")
                if result and isinstance(result, list) and len(result) > 0:
                    mem = result[0]
                    if isinstance(mem, dict) and 'result' in mem:
                        pending_mems.extend(mem['result'])
                    elif isinstance(mem, dict):
                        pending_mems.append(mem)
            except Exception as e:
                logger.warning(f"Failed to fetch memory {mem_id}: {e}")
        
        if not pending_mems:
            logger.debug(f"[Dreaming] No valid memories in batch {batch.batch_id}")
            self.memory.batch_manager.complete_batch(batch.batch_id)
            return
        
        # 记录发送给 LLM 的 ID
        sent_ids = [str(m.get('id', '')) for m in pending_mems if m.get('id')]
        self.memory.batch_manager.mark_sent_to_llm(batch.batch_id, sent_ids)
        
        # 准备 LLM 输入
        input_list = []
        for i, mem in enumerate(pending_mems):
            input_list.append({
                "id": str(i + 1),
                "memory": mem.get('content', '')
            })
            
        # LLM Prompt
        prompt = f"""你是记忆重构架构师。

### 输入数据（这些是语义相关的记忆，来自同一次检索）：
{json.dumps(input_list, ensure_ascii=False, indent=2)}
注意：对话日志是由语音转录生成的，因此可能存在错别字或谐音字以及无意义的错乱文字，请进行修正。

### 处理逻辑：
- 合并：将所有可以合并的记忆合并成一条。
- 深刻：提取深层洞察，反映主体的性格、偏好、潜在意识。
- 矛盾：如有矛盾，保留最新信息。
- 每段对话中可能包含多个不同的事实，请把它分离成多个"memory"

### 输出格式 (仅 JSON 列表):
[
  {{"memory": "[日期+时间] [事实] [简短的深刻洞察]"}},
  {{"memory": "[日期+时间] [事实] [简短的深刻洞察]"}}
]
"""
        
        try:
            if not self.llm_client:
                logger.warning("[Dreaming] No LLM client, skipping batch consolidation")
                return
                
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are a memory consolidator. Output JSON only."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.5
            )
            
            content = response.choices[0].message.content.strip()
            
            # Clean markdown
            if content.startswith("```json"): 
                content = content.split("\n", 1)[1]
            if content.endswith("```"): 
                content = content.rsplit("\n", 1)[0]
            
            consolidated = json.loads(content)
            if isinstance(consolidated, dict):
                consolidated = consolidated.get("memories", [consolidated])
            
            # 1. 归档旧记忆
            for mem in pending_mems:
                mem_id = mem.get('id', '')
                if mem_id:
                    await self.memory.db.query(f"UPDATE {mem_id} SET status = 'archived';")
            
            # 2. 插入新记忆
            for item in consolidated:
                raw_text = item.get("memory", "")
                if not raw_text: continue
                
                vector = [0.0] * 384
                if hasattr(self.memory, 'encoder') and self.memory.encoder:
                    try:
                        vector = self.memory.encoder(raw_text)
                    except:
                        pass
                
                await self.memory.add_episodic_memory(
                    character_id=self.character_id,
                    content=raw_text,
                    embedding=vector,
                    status="active"
                )
            
            # 3. 完成批次
            self.memory.batch_manager.complete_batch(batch.batch_id)
            
            logger.info(f"[Dreaming] 📦 Batch {batch.batch_id}: {len(pending_mems)} -> {len(consolidated)} memories")
            
        except Exception as e:
            logger.error(f"[Dreaming] Batch consolidation failed: {e}")
            self.memory.batch_manager.fail_batch(batch.batch_id, str(e))


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
        if not self.llm_client:
            logger.warning("[Soul Evolution] No LLM client available")
            return
        
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
        
        # 3. 构建 Prompt
        system_prompt = """You are a master-level psychology expert. Your goal is to evolve the internal state of a character based on their recent experiences and past memories.

You must output a valid JSON object strictly following the structure below.

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
    "current_mood": "(choose from: [happy], [sad], [angry], [neutral], [tired], [excited], [shy], [obsessed], [confused])"
}
"""

        user_prompt = f"""Current State:
- Traits: {current_traits}
- Big Five: {current_big_five}
- PAD Model: {current_pad}
- Current Mood: {current_mood}

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
            logger.info(f"[Soul Evolution] 🧠 Calling LLM for Soul Evolution (JSON Mode)...")
            
            response = self.llm_client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.4,  # Slightly higher temp to encourage change
                response_format={"type": "json_object"} if hasattr(self.llm_client, 'response_format') else None
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
