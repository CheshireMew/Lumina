"""Character Management Router."""
import logging
from fastapi import APIRouter, Depends, HTTPException
from routers.deps import get_character_service, get_optional_soul_service, get_optional_system_plugin_manager
from schemas.character import CharacterConfig, CharacterListResponse

logger = logging.getLogger("CharacterRouter")

router = APIRouter(prefix="/characters", tags=["Characters"])


@router.get("", response_model=CharacterListResponse)
async def list_characters(character_service=Depends(get_character_service)):
    """List all available characters"""
    try:
        return {"characters": character_service.list_characters()}
    except Exception as e:
        logger.error(f"[API] Error listing characters: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/models")
async def list_models(
    character_service=Depends(get_character_service),
    system_plugin_manager=Depends(get_optional_system_plugin_manager),
):
    """List available Live2D models via Avatar Server"""
    try:
        return {"models": character_service.list_live2d_models(system_plugin_manager)}
    except Exception as e:
        logger.error(f"[API] Error listing models: {e}")
        return {"models": []}


@router.get("/{character_id}/config", response_model=CharacterConfig)
async def get_character_config(character_id: str, character_service=Depends(get_character_service)):
    """Get character config"""
    try:
        return character_service.load_config(character_id)
    except FileNotFoundError:
        return CharacterConfig(id=character_id, name=character_id, displayName=character_id)
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error getting character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/{character_id}/config")
async def update_character_config(
    character_id: str,
    config: CharacterConfig,
    character_service=Depends(get_character_service),
    soul_service=Depends(get_optional_soul_service),
):
    """Update character config"""
    _ = soul_service
    try:
        logger.info(f"[API] update_character_config for: {character_id}")
        character_service.save_config(
            character_id,
            config.model_copy(update={"id": character_id}),
        )
        logger.info(f"[API] Config saved for {character_id}")
        return {"status": "ok", "character_id": character_id}
    except ValueError as e:
        raise HTTPException(status_code=403, detail=str(e))
    except Exception as e:
        logger.error(f"[API] Error updating character config: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/{character_id}")
async def delete_character(character_id: str, character_service=Depends(get_character_service)):
    """Delete character"""
    try:
        deleted = character_service.delete_character(character_id)
        if deleted:
            return {"status": "ok", "message": f"Character {character_id} deleted"}
        return {"status": "skipped", "message": "Character not found"}
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[API] Error deleting character: {e}")
        raise HTTPException(status_code=500, detail=str(e))
