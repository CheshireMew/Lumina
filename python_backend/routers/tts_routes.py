import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from starlette.background import BackgroundTask

from routers.deps import get_config_controller, get_container
from .worker_proxy import get_worker_control_url, proxy_json_request
from services.http_client import get_http_client
from schemas.api_contracts import (
    OperationStatusResponse,
    TtsSynthesisRequest,
    TtsSwitchRequest,
    TtsModelListResponse,
    TtsVoiceInfo,
)

logger = logging.getLogger("TTSProxy")

router = APIRouter(prefix="/capabilities/tts", tags=["TTS"])


@router.get("/health")
async def health(container=Depends(get_container)):
    response = await proxy_json_request("tts", "GET", "/health", container=container)
    return response.json()


@router.get("/models/list", response_model=TtsModelListResponse)
async def list_models(container=Depends(get_container)):
    response = await proxy_json_request("tts", "GET", "/models/list", container=container)
    return response.json()


@router.post("/models/switch", response_model=OperationStatusResponse)
async def switch_model(req: TtsSwitchRequest, config_service=Depends(get_config_controller), container=Depends(get_container)):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
        raise HTTPException(status_code=400, detail="Missing driver_id or model_name")

    response = await proxy_json_request("tts", "POST", "/models/switch", req.model_dump(exclude_none=True), container=container)
    payload = response.json()
    if payload.get("status") == "ok":
        config_service.set_selected_provider("tts", driver_id)
    return payload


@router.get("/voices", response_model=list[TtsVoiceInfo])
async def list_voices(engine: Optional[str] = None, container=Depends(get_container)):
    path = "/voices"
    if engine:
        path += f"?engine={engine}"
    response = await proxy_json_request("tts", "GET", path, container=container)
    return response.json()


@router.post("/synthesize")
async def synthesize(req: TtsSynthesisRequest, container=Depends(get_container)):
    url = f"{await get_worker_control_url('tts', container)}/synthesize"
    upstream = None
    try:
        client = await get_http_client()
        request = client.build_request(
            "POST",
            url,
            json=req.model_dump(exclude_none=True),
            timeout=60.0,
        )
        upstream = await client.send(request, stream=True)
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="TTS worker offline") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="TTS worker timeout") from exc

    if upstream.status_code >= 400:
        detail = (await upstream.aread()).decode("utf-8", errors="replace")
        await upstream.aclose()
        raise HTTPException(status_code=upstream.status_code, detail=detail)

    return StreamingResponse(
        upstream.aiter_bytes(),
        media_type=upstream.headers.get("content-type", "audio/mpeg"),
        background=BackgroundTask(upstream.aclose),
    )
