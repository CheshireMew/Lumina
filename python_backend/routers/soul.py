"""
Soul/Personality Router
Includes: /soul, /soul/mutate, /soul/switch_character, /galgame etc.

Refactored: Removed inject_dependencies
"""
import os
import json
import logging
from typing import Dict, Optional
from pydantic import BaseModel
from fastapi import APIRouter, HTTPException, BackgroundTasks

from schemas.requests import UpdateIdentityRequest, UpdateUserNameRequest

logger = logging.getLogger("SoulRouter")

router = APIRouter(tags=["Soul"])

# Helper functions to access services
def _get_soul_client():
    from services.container import services
    if not services.soul_client:
         raise HTTPException(status_code=503, detail="Soul Service not initialized")
    return services.soul_client

def _get_heartbeat_service():
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service("heartbeat_service") if bus else None


class SwitchCharacterRequest(BaseModel):
    character_id: str


@router.get("/soul/{character_id}")
async def get_soul_data(character_id: str):
    """Get evolved personality data (Read-only)"""
    try:
        from soul_manager import SoulManager
        soul = SoulManager(character_id)
        return soul.soul
    except Exception as e:
        logger.error(f"[API] Error getting soul data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/soul")
async def get_soul():
    """Get Soul State"""
    soul_client = _get_soul_client()
    try:
        # Reload to get latest data
        soul_client.soul = soul_client._load_soul()
        soul_client.state = soul_client._load_state()
        soul_client.profile = soul_client._merge_profile()
        
        # 娉ㄥ叆鍏崇郴鏍囩
        if "relationship" in soul_client.profile:
            stage_info = soul_client.get_relationship_stage()
            soul_client.profile["relationship"]["current_stage_label"] = stage_info["label"]
        
        # Inject System Prompt (Static) and Dynamic Instruction
        try:
            soul_client.profile["system_prompt"] = soul_client.render_static_prompt()
            soul_client.profile["dynamic_instruction"] = soul_client.render_dynamic_instruction()
        except Exception as e:
            logger.warning(f"[API] Failed to render prompts: {e}")
        
        return soul_client.profile
    except Exception as e:
        logger.error(f"[API] Error in /soul endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/interact")
async def register_interaction():
    """
    Centralized Endpoint to signal User Activity.
    """
    soul_client = _get_soul_client()
    try:
        soul_client.update_last_interaction()
        return {
            "status": "ok", 
            "timestamp": soul_client.state.get("last_interaction"),
            "message": "Heartbeat reset"
        }
    except Exception as e:
        logger.error(f"[API] Interaction update failed: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest):
    """Switch to specified character"""
    # Note: We don't need to inject global soul_client variable anymore, 
    # but we need to UPDATE the global soul_client instance in the container.
    # Because services.soul_client IS the singleton instance used by the app.
    
    from services.container import services
    
    try:
        from soul_manager import SoulManager
        
        character_id = request.character_id
        logger.info(f"[API] Switching to character: {character_id}")
        
        # 1. 閲嶆柊鍒濆鍖?SoulManager
        new_soul_client = SoulManager(character_id=character_id)
        new_soul_client.soul = new_soul_client._load_soul()
        new_soul_client.state = new_soul_client._load_state()
        new_soul_client.profile = new_soul_client._merge_profile()
        
        # UPDATE Container!
        services.soul_client = new_soul_client
        
        character_name = new_soul_client.profile.get("identity", {}).get("name", character_id)
        logger.info(f"[API] 鉁?Switched to character: {character_name}")
        
        # 3. 鏇存柊 Heartbeat Service
        heartbeat_service = _get_heartbeat_service()
        if heartbeat_service:
            heartbeat_service.soul = new_soul_client
            logger.info(f"[API] Heartbeat service updated")

        logger.info(f"[API] Character switch complete for '{character_id}'")
        
        return {
            "status": "success",
            "character_id": character_id,
            "character_name": character_name,
            "system_prompt": new_soul_client.render_static_prompt(),
            "dynamic_instruction": new_soul_client.render_dynamic_instruction()
        }
    except Exception as e:
        logger.error(f"[API] Failed to switch character: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/update_identity")
async def update_identity(request: UpdateIdentityRequest):
    """Update Identity"""
    soul_client = _get_soul_client()
    try:
        soul_client.profile["identity"]["name"] = request.name
        soul_client.profile["identity"]["description"] = request.description
        soul_client.save_profile()
        logger.info(f"[API] Updated identity: name={request.name}")
        return {"status": "updated", "identity": soul_client.profile["identity"]}
    except Exception as e:
        logger.error(f"[API] Failed to update identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/update_user_name")
async def update_user_name(request: UpdateUserNameRequest):
    """Update User Name"""
    soul_client = _get_soul_client()
    try:
        soul_client.profile["relationship"]["user_name"] = request.user_name
        soul_client.save_profile()
        logger.info(f"[API] Updated user_name: {request.user_name}")
        return {"status": "updated", "user_name": request.user_name}
    except Exception as e:
        logger.error(f"[API] Failed to update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/soul/user_name_bulk")
async def bulk_update_user_name(request: UpdateUserNameRequest):
    """
    Bulk update user_name for ALL characters on disk.
    """
    soul_client = _get_soul_client()
    try:
        new_name = request.user_name
        
        count = soul_client.bulk_update_user_name(new_name)
        
        logger.info(f"[API] Bulk updated user_name to '{new_name}' for {count} characters via SoulManager.")
        
        # Sync active profile memory
        soul_client.profile.setdefault("relationship", {})["user_name"] = new_name
        
        return {"status": "ok", "updated_count": count, "user_name": new_name}
        
    except Exception as e:
        logger.error(f"[API] Failed to bulk update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))
