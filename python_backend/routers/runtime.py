import logging

from fastapi import APIRouter, Depends, Request, HTTPException

from core.runtime import get_capability_contract, list_capability_contracts
from routers.deps import get_runtime_service_dep

logger = logging.getLogger("RuntimeRouter")

router = APIRouter(prefix="/runtime", tags=["Runtime"])


@router.get("/contracts")
async def list_runtime_contracts():
    return {"contracts": list_capability_contracts()}


@router.get("/capabilities")
async def list_runtime_capabilities(request: Request, runtime=Depends(get_runtime_service_dep)):
    base_url = str(request.base_url).rstrip("/")
    return {
        "capabilities": [
            runtime.get_capability_runtime("stt", base_url),
            runtime.get_capability_runtime("tts", base_url),
            runtime.get_capability_runtime("llm", base_url),
            runtime.get_capability_runtime("memory", base_url),
        ]
    }


@router.get("/capabilities/{capability}")
async def get_runtime_capability(capability: str, request: Request, runtime=Depends(get_runtime_service_dep)):
    if not get_capability_contract(capability):
        raise HTTPException(status_code=404, detail=f"Unknown capability: {capability}")
    base_url = str(request.base_url).rstrip("/")
    return runtime.get_capability_runtime(capability, base_url)
