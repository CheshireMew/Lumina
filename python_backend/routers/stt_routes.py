
import logging
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, WebSocket
from pydantic import BaseModel

from app_config import config as app_settings
from routers.deps import get_config_controller, get_container, get_runtime_service_dep
from .worker_proxy import proxy_json_request

logger = logging.getLogger("STTProxy")

router = APIRouter(prefix="/stt", tags=["STT"])

# --- Data Models (Preserved for API Compatibility) ---

class SwitchModelRequest(BaseModel):
    model_name: str

class UnifiedAudioConfig(BaseModel):
    device_name: Optional[str] = None
    enable_voiceprint_filter: Optional[bool] = None
    voiceprint_threshold: Optional[float] = None
    voiceprint_profile: Optional[str] = None
    speech_start_threshold: Optional[float] = None
    speech_end_threshold: Optional[float] = None
    min_speech_frames: Optional[int] = None

class ProviderConfigRequest(BaseModel):
    id: str
    key: str
    value: Any

# --- Endpoints ---

@router.get("/health")
async def health(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/health", container=container)
    return response.json()

@router.get("/models/list")
async def get_models(container=Depends(get_container)):
    """Proxy: List available STT models"""
    response = await proxy_json_request("stt", "GET", "/models/list", container=container)
    return response.json()

@router.post("/models/switch")
async def switch_model(payload: SwitchModelRequest, config_service=Depends(get_config_controller), container=Depends(get_container)):
    """Proxy: Switch STT Model (and persist in Main)"""
    # 1. Forward to Worker
    response = await proxy_json_request("stt", "POST", "/models/switch", payload.dict(), container=container)
    resp = response.json()
    
    # 2. If success, persist in Main (Single Source of Truth)
    if resp.get("status") == "ok":
        config_service.set_selected_provider("stt", payload.model_name)
        
    return resp

# --- Audio Config ---

@router.get("/audio/devices")
async def list_audio_devices(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/audio/devices", container=container)
    return response.json()

@router.post("/audio/config")
async def update_audio_config(request: UnifiedAudioConfig, container=Depends(get_container)):
    response = await proxy_json_request("stt", "POST", "/audio/config", request.dict(exclude_none=True), container=container)
    return response.json()

@router.get("/status/voiceprint")
@router.get("/voiceprint/status")
async def get_voiceprint_status(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/status/voiceprint", container=container)
    return response.json()

@router.get("/audio/status")
async def get_audio_status(container=Depends(get_container)):
    response = await proxy_json_request("stt", "GET", "/audio/status", container=container)
    return response.json()

# --- Lifecycle Proxies ---

@router.post("/provider/config")
async def update_provider_config(req: ProviderConfigRequest, container=Depends(get_container)):
    """Proxy provider config changes to the STT worker."""
    payload = {
        "target_id": req.id,
        "key": req.key,
        "value": req.value
    }
    response = await proxy_json_request("stt", "POST", "/lipp/v1/config", payload, container=container)
    return response.json()

# --- WebSocket Stub ---

@router.websocket("/ws/stt")
async def websocket_stub(websocket: WebSocket, runtime=Depends(get_runtime_service_dep)):
    """
    STT WebSockets must connect directly to the Worker Port (default 8001).
    We cannot easily proxy WebSockets in FastAPI without performance loss.
    """
    await websocket.accept()
    snapshot = runtime.get_capability_runtime("stt", app_settings.network.memory_url)
    await websocket.send_json({
        "error": "Connect to the signed STT stream URL from /runtime/capabilities/stt",
        "url": snapshot.get("stream_url"),
    })
    await websocket.close(code=1008, reason="Redirect to Worker Port")

