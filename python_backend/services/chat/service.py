import logging
from dataclasses import dataclass
from typing import Any, AsyncGenerator, Dict, List, Optional

from core.protocol import EventPacket
from services.companion.context import CompanionContext, CompanionContextResolver
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
        interaction_recorder: CompanionInteractionRecorder,
    ):
        if pipeline is None:
            raise ValueError("ChatTurnService requires ChatPipeline")
        if session_manager is None:
            raise ValueError("ChatTurnService requires SessionManager")
        if context_resolver is None:
            raise ValueError("ChatTurnService requires CompanionContextResolver")
        if interaction_recorder is None:
            raise ValueError("ChatTurnService requires CompanionInteractionRecorder")

        self.pipeline = pipeline
        self.session_manager = session_manager
        self.context_resolver = context_resolver
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

        messages = await self.build_turn_messages(
            request.companion_context,
            text,
            history_limit=request.history_limit,
        )

        # Fresh sessions should not retrieve previous conversations as context.
        enable_rag_for_turn = len(messages) > 1

        async for token in self.stream_response(
            messages=messages,
            companion_context=request.companion_context,
            model=request.model,
            enable_rag=enable_rag_for_turn,
            user_name=request.user_name,
        ):
            yield TurnStreamEvent(
                kind="delta",
                payload={"content": token},
            )

        yield TurnStreamEvent(kind="ended", payload={})

    async def build_turn_messages(
        self,
        companion_context: CompanionContext,
        text: str,
        history_limit: int = 10,
    ) -> List[Dict[str, Any]]:
        messages: List[Dict[str, Any]] = []
        session_manager = self.session_manager
        try:
            state = await session_manager.load_session(companion_context)
            history = getattr(state, "short_term_history", []) or []
            messages.extend(
                {"role": item["role"], "content": item["content"]}
                for item in history[-history_limit:]
                if item.get("role") and item.get("content")
            )
        except Exception as exc:
            logger.error("Failed to load session for chat turn: %s", exc)

        messages.append({"role": "user", "content": text})
        return messages

    async def stream_response(
        self,
        *,
        messages: List[Dict[str, Any]],
        companion_context: CompanionContext,
        model: Optional[str] = None,
        temperature: float = 0.7,
        stream: bool = True,
        enable_rag: bool = True,
        enable_tools: bool = True,
        save_history: bool = True,
        log_memory: bool = True,
        user_name: Optional[str] = None,
    ) -> AsyncGenerator[str, None]:
        final_response = ""
        user_msg = next(
            (m.get("content", "") for m in reversed(messages) if m.get("role") == "user"),
            "",
        )

        async for token in self.pipeline.run(
            messages,
            companion_context=companion_context,
            stream=stream,
            model=model,
            temperature=temperature,
            enable_rag=enable_rag,
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
