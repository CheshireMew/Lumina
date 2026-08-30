import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.protocol import EventPacket
from services.companion.context import CompanionContext, CompanionContextResolver
from services.companion.context_pack import CompanionContextPackBuilder
from services.companion.interaction import CompanionInteraction, CompanionInteractionRecorder

logger = logging.getLogger("ChatTurnService")


@dataclass(frozen=True)
class TextTurnRequest:
    turn_id: str
    client_id: str
    generation: int
    text: str
    companion_context: CompanionContext
    user_name: Optional[str] = None
    model: Optional[str] = None
    mode: str = "chat"
    history_limit: int = 10


@dataclass(frozen=True)
class TurnStreamEvent:
    kind: str
    payload: Dict[str, Any]


class ChatTurnService:
    """Single orchestration boundary for all chat entry points."""

    def __init__(
        self,
        *,
        pipeline: Any,
        session_manager: Any,
        context_resolver: CompanionContextResolver,
        context_pack_builder: CompanionContextPackBuilder,
        interaction_recorder: CompanionInteractionRecorder,
    ):
        if pipeline is None:
            raise ValueError("ChatTurnService requires ChatPipeline")
        if session_manager is None:
            raise ValueError("ChatTurnService requires SessionManager")
        if context_resolver is None:
            raise ValueError("ChatTurnService requires CompanionContextResolver")
        if context_pack_builder is None:
            raise ValueError("ChatTurnService requires CompanionContextPackBuilder")
        if interaction_recorder is None:
            raise ValueError("ChatTurnService requires CompanionInteractionRecorder")

        self.pipeline = pipeline
        self.session_manager = session_manager
        self.context_resolver = context_resolver
        self.context_pack_builder = context_pack_builder
        self.interaction_recorder = interaction_recorder

    def build_text_turn_request(self, packet: EventPacket) -> TextTurnRequest:
        payload = packet.payload or {}
        context = self.context_resolver.from_packet(packet)
        return TextTurnRequest(
            turn_id=str(packet.turn_id or packet.trace_id),
            client_id=packet.client_id,
            generation=packet.generation,
            text=str(payload.get("text") or ""),
            companion_context=context,
            user_name=context.user_name,
            model=payload.get("model"),
            history_limit=self._history_limit(),
        )

    def _history_limit(self) -> int:
        config = getattr(self.session_manager, "config", None)
        memory = getattr(config, "memory", None)
        value = int(getattr(memory, "history_limit", 10) or 10)
        llm = getattr(config, "llm", None)
        routes = getattr(llm, "routes", {}) if llm is not None else {}
        chat_route = routes.get("chat") if isinstance(routes, dict) else None
        if getattr(chat_route, "provider_id", None) == "free_tier":
            value = min(value, 5)
        return max(1, value)

    async def stream_text_turn(
        self,
        request: TextTurnRequest,
    ) -> AsyncGenerator[TurnStreamEvent, None]:
        text = request.text.strip()
        if not text:
            return

        yield TurnStreamEvent(
            kind="started",
            payload={"mode": request.mode},
        )

        context_pack = await self.context_pack_builder.build(
            companion_context=request.companion_context,
            user_message=text,
            history_limit=request.history_limit,
            enable_memory=True,
        )

        async for chunk in self.stream_response(
            context_pack=context_pack,
            companion_context=request.companion_context,
            model=request.model,
            user_name=request.user_name,
            turn_id=request.turn_id,
            defer_post_turn=True,
        ):
            content = str(chunk.get("content") or "")
            reasoning = str(chunk.get("reasoning") or "")
            if reasoning:
                yield TurnStreamEvent(
                    kind="reasoning",
                    payload={"content": reasoning},
                )
            if content:
                yield TurnStreamEvent(
                    kind="delta",
                    payload={"content": content},
                )

        yield TurnStreamEvent(kind="ended", payload={"status": "completed"})

    async def stream_response(
        self,
        *,
        companion_context: CompanionContext,
        context_pack: Any,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
        stream: bool = True,
        enable_tools: bool = True,
        save_history: bool = True,
        log_memory: bool = True,
        user_name: Optional[str] = None,
        turn_id: Optional[str] = None,
        defer_post_turn: bool = False,
    ) -> AsyncGenerator[Dict[str, str], None]:
        final_response = ""
        final_reasoning = ""
        user_msg = context_pack.user_message

        async for chunk in self.pipeline.run(
            context_pack=context_pack,
            stream=stream,
            model=model,
            temperature=temperature,
            enable_tools=enable_tools,
        ):
            normalized = chunk if isinstance(chunk, dict) else {"content": str(chunk)}
            content = str(normalized.get("content") or "")
            final_response += content
            final_reasoning += str(normalized.get("reasoning") or "")
            yield {
                "content": content,
                "reasoning": str(normalized.get("reasoning") or ""),
            }

        if user_msg and final_response:
            interaction = CompanionInteraction(
                companion_context=companion_context,
                user_message=user_msg,
                assistant_message=final_response,
                turn_id=turn_id,
                assistant_reasoning=final_reasoning,
                user_name=user_name,
                save_history=save_history,
                log_memory=log_memory,
            )
            if defer_post_turn:
                schedule = getattr(self.interaction_recorder, "schedule", None)
                if callable(schedule):
                    await schedule(interaction)
                else:
                    await self.interaction_recorder.record(interaction)
            else:
                await self.interaction_recorder.record(interaction)

    async def collect_response(self, **kwargs) -> str:
        content = ""
        async for chunk in self.stream_response(**kwargs):
            content += str(chunk.get("content") or "")
        return content
