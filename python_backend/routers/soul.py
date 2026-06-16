"""Soul and personality routes."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from routers.deps import get_soul_service

logger = logging.getLogger("SoulRouter")

router = APIRouter(tags=["Soul"])


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
        return {
            "status": "ok", 
            "message": "Heartbeat reset"
        }
    except Exception as e:
        logger.error(f"[API] Interaction update failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
