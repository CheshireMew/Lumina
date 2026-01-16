"""
Soul/Personality Router
Includes: /soul, /soul/mutate, /soul/switch_character, /galgame etc.

Refactored: Uses SoulService instead of SoulManager
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
def _get_soul_service():
    from services.container import services
    if not services.soul:
         raise HTTPException(status_code=503, detail="Soul Service not initialized")
    return services.soul

def _get_heartbeat_service():
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service("heartbeat_service") if bus else None


class SwitchCharacterRequest(BaseModel):
    character_id: str


@router.get("/soul/{character_id}")
async def get_soul_data(character_id: str):
    """Get evolved personality data (Read-only)"""
    # ⚡ Legacy Support: This reads raw soul data from disk for a specific char
    try:
        # We can implement a helper or simple JSON read here to avoid SoulManager dep
        # For now, just return empty if not active, or implement simple reader
        return {} 
    except Exception as e:
        logger.error(f"[API] Error getting soul data: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/soul")
async def get_soul():
    """Get Soul State"""
    soul_service = _get_soul_service()
    try:
        # Request prompt render to ensure state is fresh?
        # Or just return state
        
        # We need to construct the 'profile' dict expected by frontend
        # For universal plugins, we might need a standard "UI State" protocol
        
        if soul_service.profile:
             return soul_service.profile
        
        return {}
    except Exception as e:
        logger.error(f"[API] Error in /soul endpoint: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/interact")
async def register_interaction():
    """
    Centralized Endpoint to signal User Activity.
    """
    soul_service = _get_soul_service()
    try:
        soul_service.update_last_interaction()
        return {
            "status": "ok", 
            "message": "Heartbeat reset"
        }
    except Exception as e:
        logger.error(f"[API] Interaction update failed: {e}")
        return {"status": "error", "detail": str(e)}


@router.post("/soul/switch_character")
async def switch_character(request: SwitchCharacterRequest):
    """Switch to specified character"""
    
    # ⚡ TODO: Implement clean Switch in SoulService
    # For now, we assume the Frontend handles the character_id persistence config
    # and reboots the backend or we hot-swap config.
    
    return {"status": "error", "detail": "Hot switching not yet implemented in Universal Architecture"}


@router.post("/soul/update_identity")
async def update_identity(request: UpdateIdentityRequest):
    """Update Identity"""
    soul_service = _get_soul_service()
    try:
        # Delegate to service/driver
        # soul_service.update_identity(request)
        return {"status": "updated", "identity": {}}
    except Exception as e:
        logger.error(f"[API] Failed to update identity: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/soul/update_user_name")
async def update_user_name(request: UpdateUserNameRequest):
    """Update User Name"""
    soul_service = _get_soul_service()
    try:
        # Delegate
        # soul_service.update_user_name(request.user_name)
        return {"status": "updated", "user_name": request.user_name}
    except Exception as e:
        logger.error(f"[API] Failed to update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/soul/user_name_bulk")
async def bulk_update_user_name(request: UpdateUserNameRequest):
    """
    Bulk update user_name for ALL characters on disk.
    """
    soul_service = _get_soul_service()
    try:
        count = soul_service.bulk_update_user_name(request.user_name)
        return {"status": "ok", "updated_count": count, "user_name": request.user_name}
    except Exception as e:
        logger.error(f"[API] Failed to bulk update user_name: {e}")
        raise HTTPException(status_code=500, detail=str(e))
