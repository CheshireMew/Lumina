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
            text=str(payload.get("text") or ""),
            companion_context=context,
            user_name=context.user_name,
            model=payload.get("model"),
        )

    async def stream_text_turn(
        self,
        request: TextTurnRequest,
    ) -> AsyncGenerator[TurnStreamEvent, None]:
        text = request.text.strip()
        if not text:
            return

        yield TurnStreamEvent(
            kind="started",
            payload={"mode": request.mode, "text": text},
        )

        context_pack = await self.context_pack_builder.build(
            companion_context=request.companion_context,
            user_message=text,
            history_limit=request.history_limit,
            enable_memory=True,
        )

        async for token in self.stream_response(
            context_pack=context_pack,
            companion_context=request.companion_context,
            model=request.model,
            user_name=request.user_name,
        ):
            yield TurnStreamEvent(
                kind="delta",
                payload={"content": token},
            )

        yield TurnStreamEvent(kind="ended", payload={})

    async def stream_response(
        self,
        *,
        companion_context: CompanionContext,
        context_pack: Any,
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = True,
        enable_tools: bool = True,
        save_history: bool = True,
        log_memory: bool = True,
        user_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        final_response = ""
        user_msg = context_pack.user_message

        async for token in self.pipeline.run(
            context_pack=context_pack,
            stream=stream,
            model=model,
            temperature=temperature,
            enable_tools=enable_tools,
        ):
            final_response += token
            yield token

        if user_msg and final_response:
            await self.interaction_recorder.record(
                CompanionInteraction(
                    companion_context=companion_context,
                    user_message=user_msg,
                    assistant_message=final_response,
                    user_name=user_name,
                    save_history=save_history,
                    log_memory=log_memory,
                )
            )

    async def collect_response(self, **kwargs) -> str:
        content = ""
        async for token in self.stream_response(**kwargs):
            content += token
        return content
