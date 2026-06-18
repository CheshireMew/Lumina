from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.protocol import EventPacket, EventType
from routers.deps import (
    get_companion_interaction_recorder,
    get_companion_runtime,
    get_soul_service,
)


router = APIRouter(prefix="/companion", tags=["Companion"])


class CompanionMessageRequest(BaseModel):
    text: str
    session_id: int = 0
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    user_name: Optional[str] = None
    model: Optional[str] = None


class CompanionControlRequest(BaseModel):
    session_id: int = 0
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

    packet = EventPacket(
        session_id=request.session_id,
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

    content = await companion_runtime.collect_text_turn(
        companion_runtime.build_text_turn_request(packet)
    )

    return {
        "session_id": request.session_id,
        "content": content,
    }


@router.post("/interrupt")
async def interrupt_companion(
    companion_runtime=Depends(get_companion_runtime),
):
    await companion_runtime.interrupt()
    return {"success": True}


@router.post("/session/reset")
async def reset_companion_session(
    request: CompanionControlRequest,
    companion_runtime=Depends(get_companion_runtime),
):
    packet = EventPacket(
        session_id=request.session_id,
        type=EventType.CONTROL_SESSION,
        source="rest.companion",
        payload={
            "action": "reset",
            "user_id": request.user_id,
            "character_id": request.character_id,
            "user_name": request.user_name,
        },
    )
    session_id = await companion_runtime.reset_session(packet)
    return {"success": True, "session_id": session_id}


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
