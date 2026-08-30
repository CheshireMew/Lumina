import logging
import asyncio
import os

from fastapi import APIRouter, Depends, Request, HTTPException

from core.runtime import get_capability_contract, list_capability_contracts, list_capability_names
from routers.deps import get_companion_context_resolver, get_runtime_service_dep
from schemas.api_contracts import RuntimeCapabilitiesResponse, RuntimeCapabilitySnapshot

logger = logging.getLogger("RuntimeRouter")

router = APIRouter(prefix="/runtime", tags=["Runtime"])


@router.get("/health")
async def health_check(context_resolver=Depends(get_companion_context_resolver)):
    context = context_resolver.resolve()
    return {
        "status": "healthy",
        "active_character_id": context.character_id,
        "runtime": {
            "product": "lumina",
            "protocolVersion": 1,
            "target": "core",
            "ownerId": os.environ.get("LUMINA_RUNTIME_OWNER", ""),
            "processId": os.getpid(),
        },
    }


@router.post("/shutdown")
async def shutdown_runtime(request: Request):
    expected_owner = os.environ.get("LUMINA_RUNTIME_OWNER", "")
    supplied_owner = request.headers.get("X-Lumina-Runtime-Owner", "")
    if expected_owner and supplied_owner != expected_owner:
        raise HTTPException(status_code=403, detail="Runtime owner mismatch")

    callback = getattr(request.app.state, "request_runtime_shutdown", None)
    if not callable(callback):
        raise HTTPException(status_code=503, detail="Runtime shutdown is unavailable")
    asyncio.get_running_loop().call_later(0.05, callback)
    return {"status": "shutting_down"}


@router.get("/network")
async def get_network_config():
    from app_config import config as app_config

    core_url = app_config.network.core_url
    return {
        "core_port": app_config.network.core_port,
        "stt_port": app_config.network.stt_port,
        "tts_port": app_config.network.tts_port,
        "vision_port": app_config.network.vision_port,
        "stt_url": f"{core_url}/capabilities/stt",
        "tts_url": f"{core_url}/capabilities/tts",
        "vision_url": f"{core_url}/capabilities/vision",
        "core_url": core_url,
        "host": app_config.network.host,
    }


@router.get("/contracts")
async def list_runtime_contracts():
    return {"contracts": list_capability_contracts()}


@router.get("/capabilities", response_model=RuntimeCapabilitiesResponse)
async def list_runtime_capabilities(request: Request, runtime=Depends(get_runtime_service_dep)):
    base_url = str(request.base_url).rstrip("/")
    return {
        "capabilities": [
            runtime.get_capability_runtime(capability, base_url)
            for capability in list_capability_names()
        ]
    }

@router.get("/capabilities/{capability}", response_model=RuntimeCapabilitySnapshot)
async def get_runtime_capability(capability: str, request: Request, runtime=Depends(get_runtime_service_dep)):
    if not get_capability_contract(capability):
        raise HTTPException(status_code=404, detail=f"Unknown capability: {capability}")
    base_url = str(request.base_url).rstrip("/")
    return runtime.get_capability_runtime(capability, base_url)
