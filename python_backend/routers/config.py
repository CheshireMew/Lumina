"""
Config Router
Includes runtime configuration and health endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from schemas.runtime_settings import RuntimeLlmSettings
from routers.deps import get_companion_context_resolver, get_config_controller

logger = logging.getLogger("ConfigRouter")

router = APIRouter(tags=["Config"])


@router.get("/config/llm", response_model=RuntimeLlmSettings)
async def get_llm_runtime_settings(config_service=Depends(get_config_controller)):
    return config_service.get_llm_runtime_settings()


@router.put("/config/llm", response_model=RuntimeLlmSettings)
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
            history_limit=payload.historyLimit,
            overflow_strategy=payload.overflowStrategy,
            provider_id=payload.providerId,
        )
        return config_service.get_llm_runtime_settings()
    except Exception as exc:
        logger.error("Failed to update LLM runtime settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_check(context_resolver=Depends(get_companion_context_resolver)):
    """Health Check"""
    context = context_resolver.resolve()
    return {
        "status": "healthy",
        "active_character_id": context.character_id,
    }

@router.get("/network")
async def get_network_config():
    """Returns network port configuration for frontend sync"""
    from app_config import config as app_config
    return {
        "memory_port": app_config.network.memory_port,
        "stt_port": app_config.network.stt_port,
        "tts_port": app_config.network.tts_port,
        "stt_url": f"{app_config.network.memory_url}/stt",
        "tts_url": f"{app_config.network.memory_url}/tts",
        "memory_url": app_config.network.memory_url,
        "host": app_config.network.host
    }
