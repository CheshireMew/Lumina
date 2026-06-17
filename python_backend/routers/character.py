"""Single character router."""
import logging

from fastapi import APIRouter, Depends, HTTPException

from routers.deps import get_character_service
from schemas.character import CharacterConfig

logger = logging.getLogger("CharacterRouter")

router = APIRouter(prefix="/character", tags=["Character"])


@router.get("/config", response_model=CharacterConfig)
async def get_character_config(character_service=Depends(get_character_service)):
    """Get the single active character config."""
    try:
        return character_service.load_config()
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config")
async def update_character_config(
    config: CharacterConfig,
    character_service=Depends(get_character_service),
):
    """Update the single active character config."""
    try:
        saved = character_service.save_config(config)
        return {"status": "ok", "character": saved}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    character_service=Depends(get_character_service),
):
    """List available avatar models."""
    try:
        return {"models": character_service.list_live2d_models()}
    except Exception as e:
        logger.error(f"[API] Error listing models: {e}")
        return {"models": []}
