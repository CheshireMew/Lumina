
import logging
import json
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, AsyncGenerator, Callable

from services.companion.context import CompanionContext
from services.companion.context_pack import CompanionContextPack

logger = logging.getLogger("ChatPipeline")
MAX_TOOL_TURNS = 5

# ==================== CONTEXT ====================

@dataclass
class PipelineContext:
    """Shared state passed through the pipeline steps."""
    # Input
    context_pack: CompanionContextPack
    companion_context: CompanionContext
    enable_tools: bool
    model_override: Optional[str]
    parameter_overrides: Dict[str, Any]
    stream: bool
    
    # Computed State
    rag_context: str = ""
    system_prompt: str = ""
    tools_def: List[Dict] = field(default_factory=list)
    final_messages: List[Dict] = field(default_factory=list)
    
    # Execution State
    llm_driver: Any = None
    target_model: str = ""
    generation_params: Dict[str, Any] = field(default_factory=dict)
    include_reasoning: bool = False

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
    def __init__(self, llm_manager, list_tools: Callable[[], list[Any]]):
        self.llm_manager = llm_manager
        self.list_tools = list_tools

    async def execute(self, ctx: PipelineContext):
        # 1. Prepare Tools
        if ctx.enable_tools:
            ctx.tools_def = [tool.get_definition() for tool in self.list_tools()]
            
        # 2. Prepare Driver
        llm_manager = self.llm_manager
        ctx.llm_driver = await llm_manager.get_driver("chat")
        ctx.target_model = ctx.model_override or llm_manager.get_model_name("chat")
        ctx.generation_params = llm_manager.get_parameters(
            "chat",
            soul_state=ctx.context_pack.current_soul_state,
        )
        ctx.generation_params.update(
            {
                key: value
                for key, value in ctx.parameter_overrides.items()
                if value is not None
            }
        )
        route = llm_manager.get_route("chat")
        ctx.include_reasoning = bool(getattr(route, "include_reasoning", False))


class LLMExecutionStep(PipelineStep):
    """
    Step 3: Streaming Execution & Tool Loop.
    """
    def __init__(self, resolve_tool: Callable[[str], Any]):
        self.resolve_tool = resolve_tool

    async def execute(self, ctx: PipelineContext):
        raise NotImplementedError("LLMExecutionStep only supports stream execution. Use run_stream()")
        
    async def run_stream(self, ctx: PipelineContext) -> AsyncGenerator[Dict[str, str], None]:
        if not ctx.llm_driver:
            raise RuntimeError("LLM Driver not prepared")

        logger.info(
            "LLM stream started model=%s messages=%s tools=%s input_chars=%s",
            ctx.target_model,
            len(ctx.final_messages),
            len(ctx.tools_def),
            sum(len(str(message.get("content") or "")) for message in ctx.final_messages),
        )
        from logger_setup import get_model_diagnostics_logger

        diagnostic_logger = get_model_diagnostics_logger()
        if diagnostic_logger:
            diagnostic_logger.info(json.dumps({
                "event": "model_input",
                "model": ctx.target_model,
                "messages": ctx.final_messages,
                "tools": ctx.tools_def,
            }, ensure_ascii=False, default=str))
        
        collected_response = ""
        collected_reasoning = ""
        started_at = time.perf_counter()

        try:
            tool_round = 0
            while True:
                tool_fragments: list[dict[str, Any]] = []
                round_content = ""
                tools = (
                    ctx.tools_def
                    if ctx.enable_tools and tool_round < MAX_TOOL_TURNS
                    else None
                )
                request_kwargs = dict(ctx.generation_params)
                temperature = float(request_kwargs.pop("temperature", 0.7))
                if tools:
                    request_kwargs["tools"] = tools

                async for chunk in await ctx.llm_driver.chat_completion(
                    ctx.final_messages,
                    model=ctx.target_model,
                    stream=ctx.stream,
                    temperature=temperature,
                    **request_kwargs,
                ):
                    normalized = chunk if isinstance(chunk, dict) else {"content": str(chunk)}
                    tool_fragments.extend(normalized.get("tool_calls") or [])
                    content = str(normalized.get("content") or "")
                    reasoning = str(normalized.get("reasoning") or "")

                    if reasoning:
                        collected_reasoning += reasoning
                        if ctx.include_reasoning:
                            yield {"content": "", "reasoning": reasoning}
                    if content:
                        collected_response += content
                        round_content += content
                        yield {"content": content, "reasoning": ""}

                tool_calls = self._merge_tool_calls(tool_fragments)
                if not tool_calls:
                    break
                if tools is None:
                    raise RuntimeError("LLM requested tools after the tool-turn limit")

                logger.info(
                    "Processing tool round=%s calls=%s",
                    tool_round + 1,
                    len(tool_calls),
                )
                ctx.final_messages.append(
                    {
                        "role": "assistant",
                        "content": round_content or None,
                        "tool_calls": tool_calls,
                    }
                )
                for tool_call in tool_calls:
                    result = await self._execute_tool(tool_call)
                    ctx.final_messages.append(
                        {
                            "role": "tool",
                            "tool_call_id": tool_call["id"],
                            "content": result,
                        }
                    )
                tool_round += 1
        finally:
            logger.info(
                "LLM stream finished model=%s output_chars=%s reasoning_chars=%s duration_ms=%s",
                ctx.target_model,
                len(collected_response),
                len(collected_reasoning),
                int((time.perf_counter() - started_at) * 1000),
            )
            if diagnostic_logger:
                diagnostic_logger.info(json.dumps({
                    "event": "model_output",
                    "model": ctx.target_model,
                    "content": collected_response,
                    "reasoning": collected_reasoning,
                }, ensure_ascii=False, default=str))
        
    async def _execute_tool(self, tool_call: dict) -> str:
        func_name = str(tool_call.get("function", {}).get("name") or "")
        args_str = str(tool_call.get("function", {}).get("arguments") or "{}")
        try:
            args = json.loads(args_str)
            if not isinstance(args, dict):
                raise ValueError("Tool arguments must be an object")
            provider = self.resolve_tool(func_name)
            if provider is None:
                raise ValueError(f"Unknown tool: {func_name}")
            result = await provider.execute(args)
            return json.dumps({"ok": True, "result": result}, ensure_ascii=False, default=str)
        except Exception as exc:
            logger.warning("Tool call failed tool=%s: %s", func_name or "unknown", exc)
            return json.dumps(
                {
                    "ok": False,
                    "error": {
                        "type": type(exc).__name__,
                        "message": str(exc),
                    },
                },
                ensure_ascii=False,
            )

    @staticmethod
    def _merge_tool_calls(fragments: list[dict[str, Any]]) -> list[dict[str, Any]]:
        merged: dict[int, dict[str, Any]] = {}
        for position, fragment in enumerate(fragments):
            index = int(fragment.get("index", position))
            current = merged.setdefault(
                index,
                {
                    "id": "",
                    "type": "function",
                    "function": {"name": "", "arguments": ""},
                },
            )
            if fragment.get("id"):
                current["id"] = str(fragment["id"])
            if fragment.get("type"):
                current["type"] = str(fragment["type"])
            function = fragment.get("function") or {}
            if function.get("name"):
                current["function"]["name"] += str(function["name"])
            if function.get("arguments"):
                current["function"]["arguments"] += str(function["arguments"])

        result = []
        for index in sorted(merged):
            tool_call = merged[index]
            if not tool_call["id"]:
                tool_call["id"] = f"tool-call-{index}"
            result.append(tool_call)
        return result



class ChatPipeline:
    """
    Orchestrator.
    """
    def __init__(
        self,
        llm_manager,
        list_tools: Callable[[], list[Any]],
        resolve_tool: Callable[[str], Any],
    ):
        self.context_step = ContextBuilderStep()
        self.tool_step = ToolPreparationStep(llm_manager, list_tools)
        self.exec_step = LLMExecutionStep(resolve_tool)

    async def run(self, **kwargs) -> AsyncGenerator[Dict[str, str], None]:
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
            parameter_overrides={
                "temperature": kwargs.get("temperature"),
                "top_p": kwargs.get("top_p"),
                "presence_penalty": kwargs.get("presence_penalty"),
                "frequency_penalty": kwargs.get("frequency_penalty"),
            },
            stream=kwargs.get("stream", True)
        )
        
        # 2. Run Preparation Steps
        # Run Tool Step first to resolve LLM Driver & Target Model (needed for RAG Tier logic)
        await self.tool_step.execute(ctx)
        await self.context_step.execute(ctx)
        
        # 3. Yield Execution
        async for token in self.exec_step.run_stream(ctx):
            yield token
