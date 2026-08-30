from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
from routers.deps import get_config_controller, get_llm_service, get_soul_service
from schemas.runtime_settings import RuntimeLlmSettings
from services.orchestrators.soul import SoulService

router = APIRouter(
    prefix="/settings/llm",
    tags=["LLM Settings"]
)

import logging

logger = logging.getLogger("LLMSettingsRouter")


@router.get("/runtime", response_model=RuntimeLlmSettings)
async def get_llm_runtime_settings(config_service=Depends(get_config_controller)):
    return config_service.get_llm_runtime_settings()


@router.put("/runtime", response_model=RuntimeLlmSettings)
async def update_llm_runtime_settings(
    payload: RuntimeLlmSettings,
    config_service=Depends(get_config_controller),
):
    try:
        config_service.update_llm_runtime(
            api_key=payload.apiKey,
            base_url=payload.baseUrl,
            model=payload.model,
            temperature=payload.temperature,
            top_p=payload.topP,
            presence_penalty=payload.presencePenalty,
            frequency_penalty=payload.frequencyPenalty,
            thinking_enabled=payload.thinkingEnabled,
            history_limit=payload.historyLimit,
            overflow_strategy=payload.overflowStrategy,
            provider_id=payload.providerId,
        )
        return config_service.get_llm_runtime_settings()
    except (KeyError, ValueError) as exc:
        logger.warning("Rejected invalid LLM runtime settings: %s", exc)
        raise HTTPException(
            status_code=400,
            detail={"code": "invalid_llm_settings", "message": str(exc)},
        ) from exc
    except Exception as exc:
        logger.error("Failed to update LLM runtime settings: %s", exc)
        raise HTTPException(
            status_code=500,
            detail={"code": "llm_settings_update_failed", "message": "模型设置保存失败。"},
        ) from exc

@router.get("/providers")
async def get_providers(llm_manager=Depends(get_llm_service)):
    return {"providers": llm_manager.list_providers()}

@router.post("/providers/{provider_id}")
async def update_provider_config(
    provider_id: str,
    config: Dict[str, Any],
    config_service=Depends(get_config_controller),
):
    try:
        # Filter allowed keys
        allowed = {"base_url", "api_key", "models", "type", "enabled"}
        updates = {k: v for k, v in config.items() if k in allowed}
        config_service.update_llm_provider(provider_id, updates)
        return {
            "status": "ok",
            "provider": config_service.config.llm.providers[provider_id],
        }
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
async def update_route(
    feature: str,
    payload: Dict[str, Any],
    config_service=Depends(get_config_controller),
):
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
            
        config_service.update_llm_route(feature, clean_updates)
        return {"status": "ok"}
    except ValueError as e:
         raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/params/{feature}")
async def get_feature_params(
    feature: str,
    llm_manager=Depends(get_llm_service),
    soul_service: SoulService = Depends(get_soul_service),
):
    """Fetch all generation parameters for a specific feature, with dynamic soul-based adjustments"""
    soul_state = None
    
    if feature in ["chat", "proactive"]:
        soul_state = soul_service.get_llm_adjustment_state() or None
        if soul_state:
            logger.info(f"[LLM Settings] Calculating dynamic params for {feature} using soul state: {soul_state}")
            
    params = llm_manager.get_parameters(feature, soul_state=soul_state)
    return params

models_router = APIRouter(
    prefix="/settings/llm/models",
    tags=["LLM Settings"]
)

@models_router.get("/list")
async def list_models(provider_id: str | None = None, llm_manager=Depends(get_llm_service)):
    """List available LLM models for frontend configuration"""
    try:
        driver = (
            await llm_manager.get_driver_for_provider(provider_id)
            if provider_id
            else await llm_manager.get_driver("chat")
        )
        if driver and hasattr(driver, "list_models"):
            return {"models": await driver.list_models()}

        raise HTTPException(
            status_code=503,
            detail=f"LLM provider '{driver.id}' does not support model listing",
        )
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error listing models: {e}")
        raise HTTPException(status_code=503, detail=str(e))
