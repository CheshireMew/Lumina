from fastapi import APIRouter, HTTPException
from typing import List, Dict, Any
from llm.manager import ProviderConfig, FeatureRoute

router = APIRouter(
    prefix="/llm-mgmt",
    tags=["LLM Management"]
)

import logging

logger = logging.getLogger("LLMManagementRouter")

def _get_soul_client():
    from services.container import services
    return services.soul_client

def _get_llm_manager():
    from services.container import services
    return services.get_llm_manager()

@router.get("/providers")
async def get_providers():
    return {"providers": _get_llm_manager().list_providers()}

@router.post("/providers/{provider_id}")
async def update_provider_config(provider_id: str, config: Dict[str, Any]):
    try:
        # Filter allowed keys
        allowed = {"base_url", "api_key", "models", "type", "enabled"}
        updates = {k: v for k, v in config.items() if k in allowed}
        _get_llm_manager().update_provider(provider_id, updates)
        return {"status": "ok", "provider": _get_llm_manager().config.providers[provider_id]}
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routes")
async def get_routes():
    # Ensure default keys exist for frontend convenience
    routes = _get_llm_manager().list_routes()
    return {"routes": routes}

@router.post("/routes/{feature}")
async def update_route(feature: str, payload: Dict[str, Any]):
    """
    Payload: { "provider_id": "...", "model": "...", "temperature": ..., "top_p": ..., "presence_penalty": ..., "frequency_penalty": ... }
    """
    try:
        provider_id = payload.get("provider_id")
        model = payload.get("model")
        temperature = payload.get("temperature")
        top_p = payload.get("top_p")
        presence_penalty = payload.get("presence_penalty")
        frequency_penalty = payload.get("frequency_penalty")
        
        if not provider_id or not model:
            raise HTTPException(status_code=400, detail="Missing provider_id or model")
            
        updates = {
            "provider_id": provider_id,
            "model": model,
            "temperature": temperature,
            "top_p": top_p,
            "presence_penalty": presence_penalty,
            "frequency_penalty": frequency_penalty
        }
        # Filter out None values to allow partial updates (and prevent Pydantic validation errors)
        clean_updates = {k: v for k, v in updates.items() if v is not None}
            
        _get_llm_manager().update_route(feature, **clean_updates)
        return {"status": "ok"}
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/params/{feature}")
async def get_feature_params(feature: str):
    """Fetch all generation parameters for a specific feature, with dynamic soul-based adjustments"""
    soul_client = _get_soul_client()
    
    soul_state = None
    
    # ⚙️ Check if Soul Evolution is enabled for dynamic adjustments
    if soul_client and feature in ["chat", "proactive"]:
        # Safety: Refresh soul profile from disk
        soul_client._load_profile()
        
        # Check Master Switch: soul_evolution_enabled
        if soul_client.config.get("soul_evolution_enabled", True):
            personality = soul_client.profile.get("personality", {})
            state = soul_client.profile.get("state", {})
            rel = soul_client.profile.get("relationship", {})
            
            soul_state = {
                "pad": personality.get("pad_model", {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5}),
                "big_five": personality.get("big_five", {"openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5}),
                "energy": state.get("energy_level", 100),
                "rel_level": rel.get("level", 0)
            }
            logger.info(f"[LLM Mgmt] Calculating dynamic params for {feature} using soul state: {soul_state}")
            
    params = llm_manager.get_parameters(feature, soul_state=soul_state)
    return params
