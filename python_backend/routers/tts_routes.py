import logging
from typing import Any, Optional

import httpx
from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from routers.deps import get_config_controller, get_container
from .worker_proxy import get_worker_control_url, proxy_json_request

logger = logging.getLogger("TTSProxy")

router = APIRouter(prefix="/tts", tags=["TTS"])


class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    emotion: Optional[str] = None
    engine: str = "driver.tts.edge"
    rate: str = "+0%"
    pitch: str = "+0Hz"


class SwitchRequest(BaseModel):
    driver_id: Optional[str] = None
    model_name: Optional[str] = None


@router.get("/health")
async def health(container=Depends(get_container)):
    response = await proxy_json_request("tts", "GET", "/health", container=container)
    return response.json()


@router.get("/models/list")
async def list_models(container=Depends(get_container)):
    response = await proxy_json_request("tts", "GET", "/models/list", container=container)
    return response.json()


@router.post("/models/switch")
async def switch_model(req: SwitchRequest, config_service=Depends(get_config_controller), container=Depends(get_container)):
    driver_id = req.driver_id or req.model_name
    if not driver_id:
        raise HTTPException(status_code=400, detail="Missing driver_id or model_name")

    response = await proxy_json_request("tts", "POST", "/models/switch", req.model_dump(exclude_none=True), container=container)
    payload = response.json()
    if payload.get("status") == "ok":
        config_service.set_selected_provider("tts", driver_id)
    return payload


@router.get("/voices")
async def list_voices(engine: Optional[str] = None, container=Depends(get_container)):
    path = "/voices"
    if engine:
        path += f"?engine={engine}"
    response = await proxy_json_request("tts", "GET", path, container=container)
    return response.json()


@router.post("/synthesize")
async def synthesize(req: TTSRequest, container=Depends(get_container)):
    url = f"{get_worker_control_url('tts', container)}/synthesize"
    try:
        async with httpx.AsyncClient(timeout=60.0) as client:
            upstream = await client.post(url, json=req.model_dump(exclude_none=True))
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail="TTS worker offline") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail="TTS worker timeout") from exc

    if upstream.status_code >= 400:
        raise HTTPException(status_code=upstream.status_code, detail=upstream.text)

    return StreamingResponse(iter([upstream.content]), media_type=upstream.headers.get("content-type", "audio/mpeg"))
