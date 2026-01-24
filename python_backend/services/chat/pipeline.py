
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator

from services.container import services

logger = logging.getLogger("ChatPipeline")

# ==================== CONTEXT ====================

@dataclass
class PipelineContext:
    """Shared state passed through the pipeline steps."""
    # Input
    original_messages: List[Dict[str, Any]]
    user_id: str
    character_id: str
    enable_rag: bool
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
    Step 1: Enhances context using registered ContextProviders.
    """
    async def execute(self, ctx: PipelineContext):
        prompts = []
        
        # Iterate over all registered providers (RAG, Soul, etc.)
        for provider in services.get_context_providers():
            try:
                if content := await provider.provide(ctx):
                    prompts.append(content)
            except Exception as e:
                logger.warning(f"ContextProvider {provider.__class__.__name__} failed: {e}")

        # Assemble System Prompt
        base_system = "You are a helpful AI assistant."
        
        if services.soul:
             try:
                 # Use unified prompt system
                 base_system = await services.soul.get_system_prompt({"pipeline": "context_builder"})
             except Exception:
                 pass
             
        ctx.system_prompt = base_system
        
        if prompts:
            # Append dynamic context
            ctx.system_prompt += "\n\n" + "\n\n".join(prompts)
            
        # Finalize Messages
        ctx.final_messages = [{"role": "system", "content": ctx.system_prompt}]
        
        # Add History
        for i, msg in enumerate(ctx.original_messages):
            if msg.get("role") != "system":
                # Inject RAG Context into the LAST User Message
                if ctx.rag_context and i == len(ctx.original_messages) - 1 and msg.get("role") == "user":
                    enhanced_content = f"{msg.get('content')}\n\n## Relevant Memories/Context:\n{ctx.rag_context}"
                    ctx.final_messages.append({"role": "user", "content": enhanced_content})
                else: 
                    ctx.final_messages.append(msg)




class ToolPreparationStep(PipelineStep):
    """
    Step 2: Prepares tools definitions and LLM driver.
    """
    async def execute(self, ctx: PipelineContext):
        # 1. Prepare Tools
        if ctx.enable_tools:
            ctx.tools_def = [t.get_definition() for t in services.get_all_tools()]
            
        # 2. Prepare Driver
        llm_manager = services.get_llm_manager()
        ctx.llm_driver = await llm_manager.get_driver("chat")
        ctx.target_model = ctx.model_override or llm_manager.get_model_name("chat")


class LLMExecutionStep(PipelineStep):
    """
    Step 3: Streaming Execution & Tool Loop.
    """
    async def execute(self, ctx: PipelineContext):
        pass
        
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
        try:
            args = json.loads(args_str)
        except Exception:
            args = {}
            
        # Dynamic Dispatch via Registry
        provider = services.get_tool_provider(func_name)
        if provider:
            try:
                return await provider.execute(args)
            except Exception as e:
                logger.error(f"Tool {func_name} failed: {e}")
                return f"Error executing tool {func_name}: {e}"
        
        return f"Error: Unknown tool '{func_name}'"



class ChatPipeline:
    """
    Orchestrator.
    """
    def __init__(self):
        self.context_step = ContextBuilderStep()
        self.tool_step = ToolPreparationStep()
        self.exec_step = LLMExecutionStep()

    async def run(self, messages: List[Dict], **kwargs) -> AsyncGenerator[str, None]:
        # 1. Init Context
        ctx = PipelineContext(
            original_messages=messages,
            user_id=kwargs.get("user_id", "default"),
            character_id=kwargs.get("character_id", "default"),
            enable_rag=kwargs.get("enable_rag", True),
            enable_tools=kwargs.get("enable_tools", True),
            model_override=kwargs.get("model", None),
            temperature=kwargs.get("temperature", 0.7),
            stream=kwargs.get("stream", True)
        )
        
        # 2. Run Preparation Steps
        # Run Tool Step first to resolve LLM Driver & Target Model (needed for RAG Tier logic)
        await self.tool_step.execute(ctx)
        await self.context_step.execute(ctx)
        
        # 3. Yield Execution & Persist History
        full_response = ""
        user_msg = next((m["content"] for m in reversed(messages) if m.get("role") == "user"), None)
        save_history = kwargs.get("save_history", True)

        async for token in self.exec_step.run_stream(ctx):
            full_response += token
            yield token

        # 4. Auto-Save to SessionManager
        if save_history and user_msg and full_response:
            try:
                sm = getattr(services, "session_manager", None)
                if sm:
                    sm.add_turn(ctx.user_id, ctx.character_id, user_msg, full_response)
            except Exception as e:
                logger.error(f"Failed to auto-save session history: {e}")
