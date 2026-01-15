"""
Dreaming System Router
Exposed via DreamingPlugin for dynamic mounting.
"""
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional, Any
import logging

logger = logging.getLogger("DreamingRouter")

class WakeUpRequest(BaseModel):
    character_id: Optional[str] = None
    batch_size: int = 10

def create_router(dreaming_service: Any) -> APIRouter:
    """
    Factory function to create router with injected service.
    """
    router = APIRouter(prefix="/dream", tags=["Dream"])

    @router.post("/wake_up")
    async def wake_up(request: WakeUpRequest = WakeUpRequest()):
        """
        Trigger Dreaming System manually or via Frontend wake-up.
        """
        if not dreaming_service:
            raise HTTPException(status_code=503, detail="Dreaming service not initialized")
        
        try:
            logger.info(f"[Dream] 馃寵 Wake up triggered manually/frontend, batch={request.batch_size}")
            
            # Use the service instance directly
            await dreaming_service.process_memories(batch_size=request.batch_size)
            
            return {
                "status": "success",
                "message": "Dreaming cycle completed",
                "character_id": getattr(dreaming_service, 'character_id', 'unknown')
            }
            
        except Exception as e:
            logger.error(f"[Dream] Wake up failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.get("/status")
    async def get_status():
        """Get Dreaming System Status"""
        if not dreaming_service:
             return {"status": "not_initialized", "message": "Dreaming service not available"}
        
        return {
            "status": "ready",
            "character_id": getattr(dreaming_service, 'character_id', 'unknown'),
            "model": getattr(dreaming_service, 'model', 'unknown')
        }

    return router
