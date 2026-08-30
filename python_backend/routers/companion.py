from typing import Optional
import uuid

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.protocol import EventPacket, EventType
from routers.deps import (
    get_companion_interaction_recorder,
    get_companion_runtime,
    get_soul_service,
)
from schemas.api_contracts import CompanionHistoryResponse


router = APIRouter(prefix="/companion", tags=["Companion"])


class CompanionMessageRequest(BaseModel):
    text: str
    session_id: int = 1
    generation: int = 1
    client_id: Optional[str] = None
    turn_id: Optional[str] = None
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    user_name: Optional[str] = None
    model: Optional[str] = None


class CompanionControlRequest(BaseModel):
    session_id: int = 1
    generation: int = 1
    client_id: Optional[str] = None
    turn_id: Optional[str] = None
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    user_name: Optional[str] = None


@router.post("/message")
async def send_companion_message(
    request: CompanionMessageRequest,
    companion_runtime=Depends(get_companion_runtime),
):
    text = request.text.strip()
    if not text:
        raise HTTPException(status_code=400, detail="text is required")

    session_id = request.session_id or 1
    client_id = request.client_id or f"rest:{uuid.uuid4()}"
    turn_id = request.turn_id or str(uuid.uuid4())
    packet = EventPacket(
        client_id=client_id,
        turn_id=turn_id,
        session_id=session_id,
        generation=request.generation,
        type=EventType.INPUT_TEXT,
        source="rest.companion",
        payload={
            "text": text,
            "user_id": request.user_id,
            "character_id": request.character_id,
            "user_name": request.user_name,
            "model": request.model,
        },
    )

    content = ""
    reasoning = ""
    status = "completed"
    async for turn_event in companion_runtime.stream_text_packet(packet):
        if turn_event.kind == "delta":
            content += str(turn_event.payload.get("content") or "")
        elif turn_event.kind == "reasoning":
            reasoning += str(turn_event.payload.get("content") or "")
        elif turn_event.kind == "ended":
            status = str(turn_event.payload.get("status") or status)

    return {
        "turn_id": turn_id,
        "session_id": session_id,
        "generation": request.generation,
        "status": status,
        "content": content,
        "reasoning": reasoning,
    }


@router.post("/interrupt")
async def interrupt_companion(
    request: CompanionControlRequest,
    companion_runtime=Depends(get_companion_runtime),
):
    interrupted = await companion_runtime.interrupt(
        client_id=request.client_id or "rest",
        session_id=request.session_id,
        turn_id=request.turn_id,
    )
    return {"success": True, "turn_ids": interrupted}


@router.post("/session/reset")
async def reset_companion_session(
    request: CompanionControlRequest,
    companion_runtime=Depends(get_companion_runtime),
):
    packet = EventPacket(
        client_id=request.client_id or "rest",
        turn_id=request.turn_id,
        session_id=request.session_id,
        generation=request.generation,
        type=EventType.CONTROL_SESSION,
        source="rest.companion",
        payload={
            "action": "reset",
            "user_id": request.user_id,
            "character_id": request.character_id,
            "user_name": request.user_name,
        },
    )
    await companion_runtime.reset_session(packet)
    return {
        "success": True,
        "session_id": request.session_id + 1,
        "generation": request.generation + 1,
    }


@router.get("/history", response_model=CompanionHistoryResponse)
async def get_companion_history(
    user_id: Optional[str] = None,
    character_id: Optional[str] = None,
    user_name: Optional[str] = None,
    session_id: int = 1,
    companion_runtime=Depends(get_companion_runtime),
):
    if companion_runtime.context_resolver is None or companion_runtime.session_manager is None:
        raise HTTPException(status_code=503, detail="Companion history is unavailable")
    context = companion_runtime.context_resolver.resolve(
        session_id=session_id,
        user_id=user_id,
        character_id=character_id,
        user_name=user_name,
    )
    messages = await companion_runtime.session_manager.get_history(context)
    return {
        "session_id": session_id,
        "messages": messages,
    }


@router.get("/state")
async def get_companion_state(soul_service=Depends(get_soul_service)):
    try:
        result = dict(soul_service.profile) if soul_service.profile else {}
        if "system_prompt" not in result:
            prompt = await soul_service.get_system_prompt()
            if prompt:
                result["system_prompt"] = prompt
        return result
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


@router.post("/activity")
async def register_companion_activity(
    interaction_recorder=Depends(get_companion_interaction_recorder),
):
    try:
        await interaction_recorder.record_activity(strict=True)
        return {"status": "ok", "message": "Heartbeat reset"}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))
