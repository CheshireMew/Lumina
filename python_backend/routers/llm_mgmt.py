from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from routers.deps import get_llm_service, get_optional_soul_service

router = APIRouter(
    prefix="/llm-mgmt",
    tags=["LLM Management"]
)

import logging

logger = logging.getLogger("LLMManagementRouter")

@router.get("/providers")
async def get_providers(llm_manager=Depends(get_llm_service)):
    return {"providers": llm_manager.list_providers()}

@router.post("/providers/{provider_id}")
async def update_provider_config(provider_id: str, config: Dict[str, Any], llm_manager=Depends(get_llm_service)):
    try:
        # Filter allowed keys
        allowed = {"base_url", "api_key", "models", "type", "enabled"}
        updates = {k: v for k, v in config.items() if k in allowed}
        llm_manager.update_provider(provider_id, updates)
        return {"status": "ok", "provider": llm_manager.config.providers[provider_id]}
    except KeyError:
        raise HTTPException(status_code=404, detail="Provider not found")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/routes")
async def get_routes(llm_manager=Depends(get_llm_service)):
    # Ensure default keys exist for frontend convenience
    routes = llm_manager.list_routes()
    return {"routes": routes}

@router.post("/routes/{feature}")
async def update_route(feature: str, payload: Dict[str, Any], llm_manager=Depends(get_llm_service)):
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
            
        llm_manager.update_route(feature, **clean_updates)
        return {"status": "ok"}
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/params/{feature}")
async def get_feature_params(
    feature: str,
    llm_manager=Depends(get_llm_service),
    soul_client=Depends(get_optional_soul_service),
):
    """Fetch all generation parameters for a specific feature, with dynamic soul-based adjustments"""
    soul_state = None
    
    if soul_client and feature in ["chat", "proactive"]:
        if hasattr(soul_client, "get_llm_adjustment_state"):
            soul_state = soul_client.get_llm_adjustment_state() or None
            if soul_state:
                logger.info(f"[LLM Mgmt] Calculating dynamic params for {feature} using soul state: {soul_state}")
            
    params = llm_manager.get_parameters(feature, soul_state=soul_state)
    return params

# --- New Models Router (for /models/list) ---
models_router = APIRouter(
    prefix="/models",
    tags=["Models"]
)

@models_router.get("/list")
async def list_models(llm_manager=Depends(get_llm_service)):
    """List available LLM models for frontend configuration"""
    try:
        # Try to find Pollinations driver first (as it has the list logic)
        driver = await llm_manager.get_driver("chat") 
        if driver and hasattr(driver, "list_models"):
            return {"models": await driver.list_models()}
            
        # Fallback: Return cached or hardcoded list if driver not available
        return {"models": ["openai", "mistral", "claude-3-haiku", "gemini", "midijourney"]}
            
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        # Graceful fallback
        return {"models": ["openai", "mistral", "claude-3-haiku", "gemini", "midijourney"]}
