
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator

from services.companion.context import CompanionContext
from services.companion.context_pack import CompanionContextPack

logger = logging.getLogger("ChatPipeline")

# ==================== CONTEXT ====================

@dataclass
class PipelineContext:
    """Shared state passed through the pipeline steps."""
    # Input
    context_pack: CompanionContextPack
    companion_context: CompanionContext
    enable_tools: bool
    model_override: Optional[str]
    temperature: float
    stream: bool
    
    # Computed State
    rag_context: str = ""
    system_prompt: str = ""
    tools_def: List[Dict] = field(default_factory=list)
    final_messages: List[Dict] = field(default_factory=list)
    
    # Execution State
    llm_driver: Any = None
    target_model: str = ""
    tool_calls_buffer: List[Dict] = field(default_factory=list)

# ==================== STEP INTERFACE ====================

class PipelineStep(ABC):
    @abstractmethod
    async def execute(self, ctx: PipelineContext):
        """Modify context in place or perform side effects."""
        pass

# ==================== CONCRETE STEPS ====================

class ContextBuilderStep(PipelineStep):
    """
    Step 1: Converts the companion context pack into LLM messages.
    """
    def __init__(self, services_container):
        self.services = services_container

    async def execute(self, ctx: PipelineContext):
        pack = ctx.context_pack
        ctx.rag_context = pack.relevant_memories
        ctx.system_prompt = pack.system_prompt
        sections = pack.prompt_sections()
        if sections:
            ctx.system_prompt += "\n\n" + "\n\n".join(sections)

        ctx.final_messages = [{"role": "system", "content": ctx.system_prompt}]

        for msg in pack.recent_session_history:
            role = msg.get("role")
            if role == "system":
                continue
            ctx.final_messages.append(msg)

        ctx.final_messages.append({"role": "user", "content": pack.user_message})


class ToolPreparationStep(PipelineStep):
    """
    Step 2: Prepares tools definitions and LLM driver.
    """
    def __init__(self, services_container):
        self.services = services_container

    async def execute(self, ctx: PipelineContext):
        # 1. Prepare Tools
        if ctx.enable_tools:
            ctx.tools_def = [t.get_definition() for t in self.services.get_all_tools()]
            
        # 2. Prepare Driver
        llm_manager = self.services.get_llm_manager()
        ctx.llm_driver = await llm_manager.get_driver("chat")
        ctx.target_model = ctx.model_override or llm_manager.get_model_name("chat")


class LLMExecutionStep(PipelineStep):
    """
    Step 3: Streaming Execution & Tool Loop.
    """
    def __init__(self, services_container):
        self.services = services_container

    async def execute(self, ctx: PipelineContext):
        raise NotImplementedError("LLMExecutionStep only supports stream execution. Use run_stream()")
        
    async def run_stream(self, ctx: PipelineContext) -> AsyncGenerator[str, None]:
        if not ctx.llm_driver:
            raise RuntimeError("LLM Driver not prepared")

        logger.info(f"[Pipeline] Streaming: {ctx.target_model}, Tools: {bool(ctx.tools_def)}")
        
        # --- LOGGING: INPUT ---
        try:
            from copy import deepcopy
            log_msgs = deepcopy(ctx.final_messages)
            logger.info(f"\n========= 📤 LLM INPUT ({ctx.target_model}) =========\n{json.dumps(log_msgs, indent=2, ensure_ascii=False)}\n================================================")
        except Exception as e:
            logger.warning(f"Failed to log LLM input: {e}")
        
        # 1. First Pass
        collected_response = ""
        
        try:
            async for chunk in await ctx.llm_driver.chat_completion(
                ctx.final_messages,
                model=ctx.target_model,
                stream=ctx.stream,
                temperature=ctx.temperature,
                tools=ctx.tools_def if ctx.enable_tools else None
            ):
                if isinstance(chunk, dict):
                    if "tool_calls" in chunk:
                        ctx.tool_calls_buffer.extend(chunk["tool_calls"])
                        continue
                    
                    # Handle DeepSeek/Reasoning Models
                    content = chunk.get("content", "")
                    reasoning = chunk.get("reasoning", "")
                    
                    # Capture reasoning in logs, but don't stream to user
                    if reasoning:
                         collected_response += f" [THINK: {reasoning}] "
                         
                    if content:
                        collected_response += content
                        yield content
                else:
                    collected_response += chunk
                    yield chunk
        finally:
            # --- LOGGING: OUTPUT (Always Log even if stream interrupted) ---
            logger.info(f"\n========= 📥 LLM OUTPUT ({ctx.target_model}) =========\n{collected_response}\n================================================")
        
        # 2. Tool Execution Loop (Multi-Turn Support)
        # [Architecture Fix] Allow up to MAX_TOOL_TURNS to support tool chains
        MAX_TOOL_TURNS = 5
        
        for tool_turn in range(MAX_TOOL_TURNS):
            if not ctx.tool_calls_buffer:
                break  # No more tool calls, exit loop
                
            logger.info(f"[Pipeline] Tool Turn {tool_turn + 1}/{MAX_TOOL_TURNS}: Processing {len(ctx.tool_calls_buffer)} tool calls...")
            
            for tool_call in ctx.tool_calls_buffer:
                result = await self._execute_tool(tool_call)
                
                # Append Context
                ctx.final_messages.append({
                    "role": "assistant",
                    "content": None,
                    "tool_calls": [tool_call]
                })
                ctx.final_messages.append({
                    "role": "tool",
                    "tool_call_id": tool_call.get("id"),
                    "content": result
                })
            
            # Clear buffer for next turn
            ctx.tool_calls_buffer = []
            
            # Continue LLM call to see if more tools are needed (or final answer)
            is_last_turn = (tool_turn == MAX_TOOL_TURNS - 1)
            
            async for chunk in await ctx.llm_driver.chat_completion(
                ctx.final_messages,
                model=ctx.target_model,
                stream=ctx.stream,
                temperature=ctx.temperature,
                tools=None if is_last_turn else ctx.tools_def  # Disable tools on last turn to force answer
            ):
                if isinstance(chunk, dict):
                    if "tool_calls" in chunk:
                        ctx.tool_calls_buffer.extend(chunk["tool_calls"])
                        continue
                    content = chunk.get("content", "")
                    if content: 
                        yield content
                else:
                    yield chunk

    async def _execute_tool(self, tool_call: dict) -> str:
        func_name = tool_call.get("function", {}).get("name")
        args_str = tool_call.get("function", {}).get("arguments", "{}")
        args = json.loads(args_str)
            
        # Dynamic Dispatch via Registry
        provider = self.services.get_tool_provider(func_name)
        if provider is None:
            raise ValueError(f"Unknown tool: {func_name}")

        return await provider.execute(args)



class ChatPipeline:
    """
    Orchestrator.
    """
    def __init__(self, services_container):
        self.services = services_container
        self.context_step = ContextBuilderStep(services_container)
        self.tool_step = ToolPreparationStep(services_container)
        self.exec_step = LLMExecutionStep(services_container)

    async def run(self, **kwargs) -> AsyncGenerator[str, None]:
        # 1. Init Context
        context_pack = kwargs.get("context_pack")
        if not isinstance(context_pack, CompanionContextPack):
            raise ValueError("ChatPipeline requires context_pack")

        companion_context = context_pack.identity
        if not isinstance(companion_context, CompanionContext):
            raise ValueError("ChatPipeline requires companion_context")

        ctx = PipelineContext(
            context_pack=context_pack,
            companion_context=companion_context,
            enable_tools=kwargs.get("enable_tools", True),
            model_override=kwargs.get("model", None),
            temperature=kwargs.get("temperature", 0.7),
            stream=kwargs.get("stream", True)
        )
        
        # 2. Run Preparation Steps
        # Run Tool Step first to resolve LLM Driver & Target Model (needed for RAG Tier logic)
        await self.tool_step.execute(ctx)
        await self.context_step.execute(ctx)
        
        # 3. Yield Execution
        async for token in self.exec_step.run_stream(ctx):
            yield token
