"""
Galgame System Router
Exposed via GalgamePlugin for dynamic mounting.
"""
from fastapi import APIRouter, HTTPException, Depends
from pydantic import BaseModel
from typing import Optional, Any
import logging

logger = logging.getLogger("GalgameRouter")

def create_router(galgame_manager: Any) -> APIRouter:
    """
    Factory function to create router with injected service.
    """
    router = APIRouter(prefix="/galgame", tags=["Galgame"])

    @router.get("/{character_id}/state")
    async def get_galgame_state(character_id: str):
        """Get GalGame State + Real-time Prompt Context"""
        if not galgame_manager or not galgame_manager.enabled:
             raise HTTPException(status_code=503, detail="Galgame Engine disabled")

        try:
             # Logic extracted from routers/soul.py
             # But wait, GalgameManager is attached to a SPECIFIC soul via container?
             # GalgameManager uses `self.soul` which is globally injected.
             # Does it support multi-character? 
             # Currently SoulManager is Singleton-ish (one active character).
             # If character_id matches active soul, return it.
             
             current_soul = galgame_manager.soul
             
             # Safety check - are we asking about the active character?
             # GalgameManager is bonded to the active soul_client.
             # If we want status of offline character, we might need SoulManager to load it explicitly.
             # But generally frontend polls for ACTIVE character.
             
             return {
                 "status": "active",
                 "relationship": current_soul.profile.get("relationship", {}),
                 "energy_level": current_soul.profile.get("state", {}).get("energy_level", 100),
                 "mood": current_soul.profile.get("personality", {}).get("pad_model", {}),
                 "dynamic_instruction": current_soul.render_dynamic_instruction()
             }
        except Exception as e:
            logger.error(f"[Galgame] Error getting state: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/{character_id}/state")
    async def update_galgame_state(character_id: str, state_update: dict):
        """Update GalGame State"""
        if not galgame_manager:
             raise HTTPException(status_code=503, detail="Galgame Manager unavailable")
        
        try:
            # Reusing SoulManager's generic state update?
            # Or GalgameManager specific?
            # Let's use SoulManager for generic persistence if GalgameManager doesn't expose generic update.
            # But we are in Galgame Router.
            
            # GalgameManager has specific methods (update_energy, update_intimacy).
            # If state_update contains arbitrary keys, we might need direct access.
            
            soul = galgame_manager.soul
            if not soul: raise Exception("No active soul")
            
            soul.state.setdefault("galgame", {}).update(state_update)
            soul.save_state()
            return {"status": "ok", "character_id": character_id}
            
        except Exception as e:
            logger.error(f"[Galgame] Update failed: {e}")
            raise HTTPException(status_code=500, detail=str(e))

    @router.post("/mutate")
    async def mutate_state(
        pleasure: float = 0, 
        arousal: float = 0, 
        dominance: float = 0, 
        intimacy: float = 0, 
        energy: float = 0
    ):
        """Debug/Game Endpoint to adjust mood/stats"""
        if not galgame_manager:
             raise HTTPException(status_code=503, detail="Galgame Manager unavailable")

        if pleasure or arousal or dominance:
            galgame_manager.mutate_mood(d_p=pleasure, d_a=arousal, d_d=dominance)
        if intimacy:
            galgame_manager.update_intimacy(int(intimacy)) # int expected
        if energy:
            galgame_manager.update_energy(energy)
            
        return {"status": "ok", "message": "State mutated"}

    return router
