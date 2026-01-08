import json
import os
import requests
import traceback
from typing import List, Dict, Any
from surreal_memory import SurrealMemory
from soul_manager import SoulManager

class Hippocampus:
    """
    The Hippocampus (海马体) is responsible for consolidating Short-term episodic memory (Conversations)
    into Long-term semantic memory (Knowledge Graph & Soul State).
    
    It acts as the bridge between raw experience and crystallized wisdom.
    """
    
    def __init__(self, memory_client: SurrealMemory = None, soul_manager: SoulManager = None, character_id: str = "default"):
        self.memory = memory_client or SurrealMemory() # Expected to be passed in strictly, but fallback ok
        self.soul = soul_manager or SoulManager()
        self.character_id = character_id.lower()  # ⚡ Track current character for isolated digestion
        
        # LLM Config
        self.api_key = os.environ.get("OPENAI_API_KEY", "ollama")
        self.base_url = os.environ.get("OPENAI_BASE_URL", "http://localhost:11434/v1")
        self.model = os.environ.get("LLM_MODEL", "deepseek-chat")

        # Fallback: Try loading from memory_config.json if using defaults
        if self.base_url == "http://localhost:11434/v1" and os.path.exists("python_backend/memory_config.json"):
            try:
                with open("python_backend/memory_config.json", "r", encoding="utf-8") as f:
                    config = json.load(f)
                    if config.get("base_url"):
                        self.base_url = config["base_url"]
                        print(f"[Hippocampus] Loaded base_url from config: {self.base_url}")
                    if config.get("api_key"):
                        self.api_key = config["api_key"]
                        print(f"[Hippocampus] Loaded api_key from config")
                    if config.get("model"):
                        self.model = config["model"]
            except Exception as e:
                print(f"[Hippocampus] ⚠️ Failed to load config file: {e}")
        
    async def process_memories(self, batch_size: int = 20, force: bool = False):
        """
        Main cognitive cycle:
        1. Fetch raw conversations.
        2. If accumulation sufficient (or forced), digest them.
        3. Extract Knowledge Graph & Soul Updates.
        4. Commit to SurrealDB & SoulManager.
        """
        print(f"[Hippocampus] 🧠 Checking for memories to digest for character: {self.character_id}...")
        
        # 1. Fetch Conversations - ⚡ NOW FILTERED BY CHARACTER
        conversations = await self.memory.get_unprocessed_conversations(limit=batch_size, agent_id=self.character_id)
        
        if not conversations:
            print(f"[Hippocampus] No new memories found for {self.character_id}.")
            return

        if len(conversations) < batch_size and not force:
            print(f"[Hippocampus] Accumulating memories... ({len(conversations)}/{batch_size})")
            return
            
        print(f"[Hippocampus] ⚡ Digesting {len(conversations)} memories...")
        
        # 2. Prepare Context
        context_text = ""
        conv_ids = []
        for conv in conversations:
            print(f"[DEBUG] Raw Conv Keys: {list(conv.keys())}")
            # Format: [Time] Narrative
            ts = str(conv.get("created_at", ""))[:16]
            
            # Fallback strategy for context
            if conv.get("narrative"):
                text = conv["narrative"]
            else:
                user_text = conv.get("user_input", "")
                ai_text = conv.get("ai_response", "")
                text = f"User: {user_text}\nAI: {ai_text}"
            
            context_text += f"[{ts}]\n{text}\n\n"
            conv_ids.append(conv['id'])
            
        # 3. Cognitive Processing (LLM)
        try:
            analysis_result = self._analyze_batch(context_text)
            
            if not analysis_result:
                print("[Hippocampus] LLM returned empty analysis.")
                return

            # 4. Commit Knowledge Graph (Facts)
            facts = analysis_result.get("facts", [])
            # Backward compatibility check
            if not facts: 
                facts = analysis_result.get("knowledge", [])
            
            # ⚡ Use current character_id instead of extracting from batch (more reliable)
            observer_id = self.character_id

            if facts:
                await self.memory.add_knowledge_graph(facts, observer_id=observer_id)
                print(f"[Hippocampus] 🕸️ Wove {len(facts)} new facts for {observer_id}.")

            # 5. Commit Insights & Evidence (New)
            insights = analysis_result.get("insights", [])
            evidence = analysis_result.get("evidence_chain", [])
            
            if insights:
                await self.memory.add_insights(insights, evidence, observer_id=observer_id)
                print(f"[Hippocampus] 💡 Generated {len(insights)} insights.")

            # 6. Mark Processed
            await self.memory.mark_conversations_processed(conv_ids)
            print(f"[Hippocampus] ✅ Digestion complete.")
            
            # 7. Validation / Pruning (Optional, maybe run less frequently)
            # await self.memory.prune_and_decay_graph() 
            
        except Exception as e:
            print(f"[Hippocampus] ❌ Cognitive Failure: {e}")
            traceback.print_exc()

    def _analyze_batch(self, context_text: str) -> Dict[str, Any]:
        """Call LLM to extract Knowledge and Soul updates."""
        
        system_prompt = """
### 角色定义
你不仅仅是一个记录员，你是一个**心理分析师**。
你需要通过阅读对话实录（Narrative），推导出其中多个人物的性格、价值观和潜在需求。

### 输入格式说明
输入是一段对话实录（Narrative），格式通常为：
`[Time] SpeakerName: Content`
或者
`[Time] (Action description)`

**关键任务**: 
- 识别对话中的主体，并统一映射为实体
- 对话中可能存在多个事实，请仔细检查，并在这种情况下分别给每个事实生成"facts"、"insights"和"evidence_chain"然后再拼接成JSON格式

### 任务目标
1. **提取事实 (Facts)**
2. **生成洞察 (Insights)**
3. **建立证据链 (Derivation)**

### 强制输出格式 (JSON)
{
    "facts": [
        {
            "subject": "EntityName",
            "relation": "RELATION_TYPE (UPPERCASE)",
            "object": "EntityName",
            "weight": 0.1 to 1.0 (Criticality: 1.0=Core Value/Trauma, 0.5=Preference, 0.1=Trivia),
            "emotion": "Context emotion",
            "context": "Short summary",
            "potential_reason": "Why is this true?"
        }
    ],
    "insights": [
        {
            "label": "Short Title (e.g. Artistic Soul)",
            "description": "Deep psychological inference about the user",
            "confidence": 0.1 to 1.0,
            "weight": 0.1 to 1.0
        }
    ],
    "evidence_chain": [
        {
            "insight_label": "Must match a label in insights",
            "fact_subject": "Must match a subject in facts",
            "fact_relation": "Must match a relation in facts",
            "fact_object": "Must match an object in facts"
        }
    ]
}

### Rules for Knowledge Graph:
1. **Facts (Level 1)**: Direct observations from the conversation. 
   - Assign `weight` based on emotional intensity and long-term relevance.
2. **Insights (Level 2)**: Abstract patterns derived from facts. 
   - e.g. Fact: "User likes Jazz" + "User plays Guitar" -> Insight: "Sophisticated Musician".
3. **Evidence**: Link every Insight to at least one Fact via `evidence_chain`.
4. **Entities**: Use precise, singular names (e.g., "Coffee", not "cups of coffee").
5. **Conflict**: If User changed their mind, output the NEW relation.
"""

        print(f"[DEBUG] Context Text: {context_text}")

        user_prompt = f"""
Input Conversations:
{context_text}

Task:
1. Extract FACTS (What happened? What does user like/do?)
2. Deriv INSIGHTS (What does this say about their personality/state?)
3. Connect them.

Output strictly valid JSON.
"""
        
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": 0.5, # Increased for creativity in insights
            "response_format": {"type": "json_object"}
        }
        
        try:
            print(f"[Hippocampus] Calling LLM ({self.model})...")
            response = requests.post(f"{self.base_url}/chat/completions", json=payload, headers={"Authorization": f"Bearer {self.api_key}"}, timeout=60)
            response.raise_for_status()
            content = response.json()['choices'][0]['message']['content']
            
            # Robust Parsing
            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].strip()
            
            print(f"[DEBUG] Raw JSON from LLM: {content}")
            
            try:
                analysis_result = json.loads(content)
                return analysis_result
            except json.JSONDecodeError as e:
                print(f"[Hippocampus] JSON Decode Error: {e}")
                print(f"[Hippocampus] Malformed JSON content: {content}")
                return {}
            
        except Exception as e:
            print(f"[Hippocampus] LLM Error: {e}")
            return {}

if __name__ == "__main__":
    # Test Stub
    import asyncio
    
    async def main():
        mem = SurrealMemory()
        await mem.connect()
        hippo = Hippocampus(mem)
        await hippo.process_memories(batch_size=1, force=True) # Force process for test
        await mem.close()

    asyncio.run(main())
