"""Single character router."""
import logging
import asyncio

from fastapi import APIRouter, Depends, HTTPException, Request

from routers.deps import get_character_service
from schemas.character import CharacterConfig
from schemas.api_contracts import CharacterModelListResponse

logger = logging.getLogger("CharacterRouter")

router = APIRouter(prefix="/settings/character", tags=["Character"])


@router.get("/config", response_model=CharacterConfig)
async def get_character_config(
    request: Request,
    character_service=Depends(get_character_service),
):
    """Get the single active character config."""
    try:
        return await asyncio.to_thread(
            character_service.load_config,
            base_url=str(request.base_url),
        )
    except FileNotFoundError as e:
        raise HTTPException(status_code=404, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/config", response_model=CharacterConfig)
async def update_character_config(
    config: CharacterConfig,
    character_service=Depends(get_character_service),
):
    """Update the single active character config."""
    try:
        saved = await asyncio.to_thread(character_service.save_config, config)
        return saved
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models", response_model=CharacterModelListResponse)
async def list_models(
    character_service=Depends(get_character_service),
):
    """List available avatar models."""
    try:
        return {
            "models": await asyncio.to_thread(character_service.list_live2d_models)
        }
    except Exception as e:
        logger.error(f"[API] Error listing models: {e}")
        return {"models": []}
