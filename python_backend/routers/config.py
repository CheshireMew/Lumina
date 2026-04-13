"""
Config Router
Includes runtime configuration and health endpoints.
"""
import logging
from fastapi import APIRouter, Depends, HTTPException

from schemas.requests import ConfigRequest
from schemas.runtime_settings import RuntimeLlmSettings
from routers.deps import get_config_controller, get_optional_soul_service

logger = logging.getLogger("ConfigRouter")

router = APIRouter(tags=["Config"])


@router.post("/configure")
async def configure_memory(config: ConfigRequest, config_service=Depends(get_config_controller)):
    """Configure LLM and memory settings without changing the active character."""

    logger.info("=== /configure Request Received ===")
    logger.info(f"BaseURL: {config.base_url}, Model: {config.model}")

    try:
        config_service.update_llm_runtime(
            api_key=config.api_key,
            base_url=config.base_url,
            model=config.model,
            history_limit=config.history_limit,
            overflow_strategy=config.overflow_strategy,
            provider_type=config.provider_type,
        )

        logger.info("✅ Configuration updated without changing character")
        return {"status": "ok", "message": "Configuration updated"}
    except Exception as e:
        logger.error(f"INIT ERROR: {e}")
        import traceback
        traceback.print_exc()
        raise HTTPException(status_code=500, detail=str(e))


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
            provider_type=payload.providerType,
        )
        return config_service.get_llm_runtime_settings()
    except Exception as exc:
        logger.error("Failed to update LLM runtime settings: %s", exc)
        raise HTTPException(status_code=500, detail=str(exc))


@router.get("/health")
async def health_check(soul_service=Depends(get_optional_soul_service)):
    """Health Check"""
    return {
        "status": "healthy",
        "soul_client": soul_service is not None
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
