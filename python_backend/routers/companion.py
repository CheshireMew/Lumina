from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from core.protocol import EventPacket, EventType
from routers.deps import get_companion_runtime


router = APIRouter(prefix="/companion", tags=["Companion"])


class CompanionMessageRequest(BaseModel):
    text: str
    session_id: int = 0
    user_id: Optional[str] = None
    character_id: Optional[str] = None
    user_name: Optional[str] = None
    model: Optional[str] = None


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
