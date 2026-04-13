"""Soul and personality routes."""
import logging
from pydantic import BaseModel
from fastapi import APIRouter, Depends, HTTPException
from routers.deps import get_soul_service

logger = logging.getLogger("SoulRouter")

router = APIRouter(tags=["Soul"])

class SwitchCharacterRequest(BaseModel):
    character_id: str


@router.get("/soul/{character_id}")
async def get_soul_data(character_id: str, soul_service=Depends(get_soul_service)):
    """Get character personality data without switching the active runtime."""
    try:
        if hasattr(soul_service, "load_character_profile"):
            return soul_service.load_character_profile(character_id)
        return {}
    except Exception as e:
        logger.error(f"[API] Error getting soul data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/galgame/{character_id}/state")
async def get_galgame_state(character_id: str, soul_service=Depends(get_soul_service)):
    """Get character interaction state from the soul data boundary."""
    try:
        return soul_service.load_galgame_state(character_id)
    except Exception as e:
        logger.error(f"[API] Error getting galgame state: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/soul")
async def get_soul(soul_service=Depends(get_soul_service)):
    """Get Soul State"""
    try:
        result = dict(soul_service.profile) if soul_service.profile else {}

        # Ensure system_prompt is included (frontend depends on it)
        if "system_prompt" not in result:
            try:
                prompt = await soul_service.get_system_prompt()
                if prompt:
                    result["system_prompt"] = prompt
            except Exception:
                pass

        return result
    except Exception as e:
        logger.error(f"[API] Error in /soul endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/interact")
async def register_interaction(soul_service=Depends(get_soul_service)):
    """
    Centralized Endpoint to signal User Activity.
    """
    try:
        soul_service.update_last_interaction()
        if hasattr(soul_service, "clear_pending_interaction"):
            soul_service.clear_pending_interaction()
        return {
            "status": "ok", 
            "message": "Heartbeat reset"
        }
    except Exception as e:
        logger.error(f"[API] Interaction update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest, soul_service=Depends(get_soul_service)):
    """Single formal character switching route."""
    try:
        soul_service.set_active_character(request.character_id)
        return {
            "status": "ok",
            "character_id": request.character_id,
            "message": f"Switched to {request.character_id}",
        }
    except Exception as e:
        logger.error(f"[API] Character switch failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
