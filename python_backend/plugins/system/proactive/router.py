from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import logging

logger = logging.getLogger("HeartbeatRouter")

router = APIRouter(tags=["Heartbeat"])

class HeartbeatReloadResponse(BaseModel):
    status: str
    heartbeat_enabled: bool
    proactive_threshold_minutes: float

def _get_soul_client():
    from services.container import services
    return services.soul_client

def _get_heartbeat_service():
    from core.events.bus import get_event_bus
    bus = get_event_bus()
    return bus.get_service("heartbeat_service") if bus else None

@router.post("/heartbeat/reload", response_model=HeartbeatReloadResponse)
async def reload_heartbeat():
    """閲嶆柊鍔犺浇蹇冭烦閰嶇疆"""
    soul_client = _get_soul_client()
    heartbeat_service = _get_heartbeat_service()
    
    if not soul_client:
        raise HTTPException(status_code=503, detail="Soul Service not ready")

    try:
        # Reload Config via Soul Client
        soul_client.config = soul_client._load_config()
        
        # Update Service
        if heartbeat_service:
            # Re-inject soul just in case reference changed (unlikely but safe)
            heartbeat_service.soul = soul_client
            
        heartbeat_enabled = soul_client.config.get("heartbeat_enabled", True)
        logger.info(f"鉂わ笍 Heartbeat config reloaded. Enabled: {heartbeat_enabled}")
        
        return {
            "status": "ok",
            "heartbeat_enabled": heartbeat_enabled,
            "proactive_threshold_minutes": soul_client.config.get("proactive_threshold_minutes", 15.0)
        }
    except Exception as e:
        logger.error(f"Failed to reload heartbeat: {e}")
        raise HTTPException(status_code=500, detail=str(e))
