
import logging
from fastapi import APIRouter, Depends, HTTPException, WebSocket

from app_config import config as app_settings
from routers.deps import get_config_controller, get_container, get_runtime_service_dep
from .worker_proxy import proxy_json_request
from schemas.api_contracts import (
    AudioDeviceListResponse,
    AudioStatusResponse,
    OperationStatusResponse,
    SttSwitchModelRequest,
    SttModelListResponse,
    UnifiedAudioConfig,
    VoiceprintStatusResponse,
)

logger = logging.getLogger("STTProxy")

router = APIRouter(prefix="/capabilities/stt", tags=["STT"])

# --- Endpoints ---

@router.get("/health")
async def health(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/health", container=container)
    return response.json()

@router.get("/models/list", response_model=SttModelListResponse)
async def get_models(container=Depends(get_container)):
    """Proxy: List available STT models"""
    response = await proxy_json_request("stt", "GET", "/models/list", container=container)
    return response.json()

@router.post("/models/switch", response_model=OperationStatusResponse)
async def switch_model(payload: SttSwitchModelRequest, config_service=Depends(get_config_controller), container=Depends(get_container)):
    """Proxy: Switch STT Model (and persist in Main)"""
    # 1. Forward to Worker
    response = await proxy_json_request("stt", "POST", "/models/switch", payload.model_dump(), container=container)
    resp = response.json()
    
    # 2. If success, persist in Main (Single Source of Truth)
    if resp.get("status") == "ok":
        config_service.set_selected_provider("stt", payload.model_name)
        
    return resp

# --- Audio Config ---

@router.get("/audio/devices", response_model=AudioDeviceListResponse)
async def list_audio_devices(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/audio/devices", container=container)
    return response.json()

@router.post("/audio/config", response_model=OperationStatusResponse)
async def update_audio_config(
    request: UnifiedAudioConfig,
    container=Depends(get_container),
    config_service=Depends(get_config_controller),
):
    payload = request.model_dump(exclude_none=True)
    response = await proxy_json_request("stt", "POST", "/audio/config", payload, container=container)
    config_service.update_audio_runtime(**payload)
    return response.json()

@router.get("/voiceprint/status", response_model=VoiceprintStatusResponse)
async def get_voiceprint_status(container=Depends(get_container)):
    audio_config = app_settings.audio
    worker_status = {}
    try:
        response = await proxy_json_request("stt", "GET", "/voiceprint/status", container=container)
        worker_status = response.json()
    except HTTPException as exc:
        logger.warning("Voiceprint worker status unavailable: %s", exc.detail)

    return {
        "enabled": audio_config.enable_voiceprint_filter,
        "loaded": bool(worker_status.get("loaded")),
        "threshold": audio_config.voiceprint_threshold,
        "profile": audio_config.voiceprint_profile,
        "profile_loaded": bool(worker_status.get("profile_loaded")),
    }

@router.get("/audio/status", response_model=AudioStatusResponse)
async def get_audio_status(container=Depends(get_container)):
    audio_config = app_settings.audio
    worker_status = {}
    try:
        response = await proxy_json_request("stt", "GET", "/audio/status", container=container)
        worker_status = response.json()
    except HTTPException as exc:
        logger.warning("Audio worker status unavailable: %s", exc.detail)

    return {
        **worker_status,
        "device_name": audio_config.device_name,
        "speech_start_threshold": audio_config.speech_start_threshold,
        "speech_end_threshold": audio_config.speech_end_threshold,
        "min_speech_frames": audio_config.min_speech_frames,
    }

# --- WebSocket Stub ---

@router.websocket("/ws/stt")
async def websocket_stub(websocket: WebSocket, runtime=Depends(get_runtime_service_dep)):
    """
    STT WebSockets must use the signed stream URL returned by the runtime endpoint.
    We cannot easily proxy WebSockets in FastAPI without performance loss.
    """
    await websocket.accept()
    snapshot = runtime.get_capability_runtime("stt", app_settings.network.core_url)
    await websocket.send_json({
        "error": "Connect to the signed STT stream URL from /runtime/capabilities/stt",
        "url": snapshot.get("stream_url"),
    })
    await websocket.close(code=1008, reason="Redirect to Worker Port")

