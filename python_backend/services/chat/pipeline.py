
import logging
import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator

from sdk.lumina.hook import HookManager
from services.chat.contracts import CHAT_HOOKS

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
    metadata: Dict[str, Any] = field(default_factory=dict)

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
    def __init__(self, services_container):
        self.services = services_container

    async def execute(self, ctx: PipelineContext):
        prompts = []
        
        # Iterate over all registered providers (RAG, Soul, etc.)
        for provider in self.services.get_context_providers():
            try:
                if content := await provider.provide(ctx):
                    prompts.append(content)
            except Exception as e:
                logger.warning(f"ContextProvider {provider.__class__.__name__} failed: {e}")

        # Assemble System Prompt
        base_system = "You are a helpful AI assistant."
        
        if self.services.soul:
             try:
                 # Use unified prompt system
                 base_system = await self.services.soul.get_system_prompt({"pipeline": "context_builder"})
             except Exception as e:
                 logger.warning(f"Failed to load system prompt from Soul: {e}")
             
        ctx.system_prompt = base_system
        
        if prompts:
            # Append dynamic context
            ctx.system_prompt += "\n\n" + "\n\n".join(prompts)
            
        # Finalize Messages
        ctx.final_messages = [{"role": "system", "content": ctx.system_prompt}]
        
        # Add History
        for i, msg in enumerate(ctx.original_messages):
            role = msg.get("role")
            if role == "system":
                continue
                
            is_last_user_msg = (ctx.rag_context and 
                              i == len(ctx.original_messages) - 1 and 
                              role == "user")
            
            if is_last_user_msg:
                # Inject RAG Context into the LAST User Message
                enhanced_content = f"{msg.get('content')}\n\n## Relevant Memories/Context:\n{ctx.rag_context}"
                ctx.final_messages.append({"role": "user", "content": enhanced_content})
            else: 
                ctx.final_messages.append(msg)




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
        try:
            args = json.loads(args_str)
        except Exception:
            args = {}
            
        # Dynamic Dispatch via Registry
        provider = self.services.get_tool_provider(func_name)
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
    def __init__(self, services_container):
        self.services = services_container
        self.context_step = ContextBuilderStep(services_container)
        self.tool_step = ToolPreparationStep(services_container)
        self.exec_step = LLMExecutionStep(services_container)
        self._hook_manager = HookManager.instance()

    async def _run_hook(self, slot: str, data: Any, metadata: Optional[Dict[str, Any]] = None) -> tuple[Any, bool]:
        hook_name = CHAT_HOOKS[slot]
        hook_manager = self._hook_manager or HookManager.instance()
        if not hook_manager:
            return data, True
        return await hook_manager.execute(hook_name, data, metadata=metadata or {})

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
        ctx.metadata = {
            "user_id": ctx.user_id,
            "character_id": ctx.character_id,
            "enable_rag": ctx.enable_rag,
            "enable_tools": ctx.enable_tools,
            "model_override": ctx.model_override,
        }

        preprocessed, should_continue = await self._run_hook(
            "input_preprocess",
            {
                "messages": ctx.original_messages,
                "options": {
                    "user_id": ctx.user_id,
                    "character_id": ctx.character_id,
                    "enable_rag": ctx.enable_rag,
                    "enable_tools": ctx.enable_tools,
                    "model": ctx.model_override,
                    "temperature": ctx.temperature,
                    "stream": ctx.stream,
                },
            },
            metadata=ctx.metadata,
        )
        if not should_continue:
            return
        if isinstance(preprocessed, dict):
            ctx.original_messages = list(preprocessed.get("messages", ctx.original_messages))
            options = preprocessed.get("options", {})
            ctx.enable_rag = options.get("enable_rag", ctx.enable_rag)
            ctx.enable_tools = options.get("enable_tools", ctx.enable_tools)
            ctx.model_override = options.get("model", ctx.model_override)
            ctx.temperature = options.get("temperature", ctx.temperature)
            ctx.stream = options.get("stream", ctx.stream)
        
        # 2. Run Preparation Steps
        # Run Tool Step first to resolve LLM Driver & Target Model (needed for RAG Tier logic)
        await self.tool_step.execute(ctx)
        _, should_continue = await self._run_hook("tool_resolve", ctx, metadata=ctx.metadata)
        if not should_continue:
            return
        await self.context_step.execute(ctx)
        _, should_continue = await self._run_hook("context_build", ctx, metadata=ctx.metadata)
        if not should_continue:
            return
        _, should_continue = await self._run_hook("generate", ctx, metadata=ctx.metadata)
        if not should_continue:
            return
        
        # 3. Yield Execution & Persist History
        full_response = ""
        user_msg = next((m["content"] for m in reversed(ctx.original_messages) if m.get("role") == "user"), None)
        save_history = kwargs.get("save_history", True)

        async for token in self.exec_step.run_stream(ctx):
            filtered_token, should_continue = await self._run_hook(
                "output_filter",
                token,
                metadata={**ctx.metadata, "mode": "stream"},
            )
            if not should_continue:
                break
            if isinstance(filtered_token, str):
                token = filtered_token
            full_response += token
            yield token

        # 4. Auto-Save to SessionManager
        if save_history and user_msg and full_response:
            try:
                sm = getattr(self.services, "session_manager", None)
                if sm:
                    await sm.add_turn(ctx.user_id, ctx.character_id, user_msg, full_response)
            except Exception as e:
                logger.error(f"Failed to auto-save session history: {e}")

        await self._run_hook(
            "post_turn",
            {
                "user_id": ctx.user_id,
                "character_id": ctx.character_id,
                "user_message": user_msg,
                "assistant_message": full_response,
                "messages": ctx.final_messages,
                "tool_calls": list(ctx.tool_calls_buffer),
            },
            metadata=ctx.metadata,
        )
