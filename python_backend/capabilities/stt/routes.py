
import logging
from typing import Any, Optional
from fastapi import APIRouter, Depends, HTTPException, WebSocket, BackgroundTasks, Request, File, UploadFile
from pydantic import BaseModel

from routers.deps import get_stt_service
from app_config import config as app_settings
from core.protocols.lipp import LippProtocol, LippLifecycleRequest, LippConfigRequest
from .runtime_state import get_stt_runtime_state
from .voiceprint_embedding import VoiceprintEmbeddingService
from .websocket_hub import SttWebSocketHub

logger = logging.getLogger("STTRouter")

router = APIRouter()

# --- Data Models (Domain Specific) ---

class SwitchModelRequest(BaseModel):
    model_name: str

class UnifiedAudioConfig(BaseModel):
    device_name: Optional[str] = None
    enable_voiceprint_filter: Optional[bool] = None
    voiceprint_threshold: Optional[float] = None
    voiceprint_profile: Optional[str] = None
    vad_aggressiveness: Optional[int] = None
    speech_start_threshold: Optional[float] = None
    speech_end_threshold: Optional[float] = None
    min_speech_frames: Optional[int] = None

# --- LIPP Handlers ---

async def stt_lifecycle_handler(payload: LippLifecycleRequest):
    """LIPP Lifecycle Implementation"""
    state = get_stt_runtime_state()
    stt_manager = state.stt_manager
    if not stt_manager: return

    logger.info(f"📢 [LIPP] Lifecycle: {payload.action} -> {payload.target_id}")
    
    if payload.action == "disable":
        if stt_manager.is_driver_active(payload.target_id):
             logger.info(f"🛑 Unloading disabled driver {payload.target_id}")
             await stt_manager.unload_active_driver()
             
    elif payload.action == "enable":
        app_settings.load_configs()
        if app_settings.get_selected_provider("stt") == payload.target_id:
             logger.info(f"🟢 Loading enabled driver {payload.target_id}")
             await stt_manager.activate(payload.target_id)

async def stt_config_handler(payload: LippConfigRequest):
    """LIPP Config Implementation"""
    state = get_stt_runtime_state()
    stt_manager = state.stt_manager
    
    logger.info(f"⚙️ [LIPP] Config: {payload.target_id} -> {payload.key}={payload.value}")
    
    config = stt_manager.update_driver_config(payload.target_id, payload.key, payload.value)

    # Hot Reload
    if payload.key in ["model_size", "fw_model_size"]:
        await stt_manager.switch_model_background(payload.value)

    return {"config": config}

async def stt_health_check():
    from core.protocols.lipp import LippHealthResponse
    state = get_stt_runtime_state()
    status = "ok"
    details = {}
    if state.audio_manager:
        if not state.audio_manager.is_running and len(state.active_websockets) > 0:
            status = "degraded"
            details["audio"] = "stalled"
    return LippHealthResponse(status=status, details=details)

# --- Mount LIPP Router ---

lipp_router = LippProtocol.create_router(
    service_name="worker:stt",
    lifecycle_handler=stt_lifecycle_handler,
    config_handler=stt_config_handler,
    health_handler=stt_health_check,
    capabilities=["stt", "vad", "voiceprint"]
)
router.include_router(lipp_router)

# --- Domain Endpoints ---

@router.get("/models/list")
async def get_models(stt_manager: Any = Depends(get_stt_service)):
    """List available STT models and their status"""
    models = []
    
    # 1. Faster Whisper
    models.append({
        "id": "faster-whisper", 
        "name": "Faster Whisper",
        "type": "local",
        "active": (stt_manager.engine_type == "faster_whisper")
    })
    
    # 2. SenseVoice (Sherpa)
    models.append({
        "id": "sense-voice",
        "name": "SenseVoice (Sherpa-ONNX)",
        "type": "local",
        "active": (stt_manager.engine_type == "sense_voice")
    })
    
    # 3. Dynamic Drivers
    for pid, drv in stt_manager.iter_drivers():
         if pid in ["driver.stt.sensevoice", "driver.stt.whisper"]: continue
         models.append({
             "id": pid,
             "name": drv.name,
             "type": "provider",
             "description": drv.description,
             "active": stt_manager.is_driver_active(pid)
         })

    return {
        "current_model": stt_manager.current_model_name,
        "active_model": stt_manager.current_model_name,
        "engine_type": stt_manager.engine_type,
        "engine": stt_manager.engine_type,
        "loading_status": stt_manager.loading_status,
        "models": models,
        "vad_status": "active"
        if get_stt_runtime_state().audio_manager and get_stt_runtime_state().audio_manager.is_running
        else "idle"
    }

@router.post("/models/switch")
async def switch_model(
    payload: SwitchModelRequest, 
    request: Request,
    background_tasks: BackgroundTasks,
    stt_manager: Any = Depends(get_stt_service)
):
    """Switch STT Model/Engine"""
    logger.info(f"Recursive Switch Request: {payload.model_name}")
    valid = False
    target = payload.model_name
    if stt_manager.has_driver(target): valid = True
    elif target in ["faster-whisper", "sense-voice"]: valid = True
        
    if not valid: raise HTTPException(status_code=400, detail=f"Unknown model/driver: {target}")

    state = get_stt_runtime_state()
    if state.audio_manager and state.audio_manager.is_running:
        state.audio_manager.stop()
        
    await stt_manager.switch_model_background(target)
    # [Config] Local Update for runtime consistency
    app_settings.set_selected_provider("stt", stt_manager.active_driver_id)

    if state.audio_manager:
        background_tasks.add_task(state.audio_manager.start)

    # [Scheme D] Active Notification to Main
    # Main process will handle persistence if needed via its own controller logic
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()

    return {"status": "ok", "active_model": stt_manager.active_driver_id}

# --- Audio Config ---

@router.get("/audio/devices")
async def list_audio_devices():
    from services.managers.audio_devices import AudioDeviceSelector

    try:
        state = get_stt_runtime_state()
        selector = (
            state.audio_manager.device_selector
            if state.audio_manager
            else AudioDeviceSelector(sample_rate=16000, frame_size=480)
        )
        devices = selector.list_input_devices(check_available=False)
        input_devices = []
        for device in devices:
            input_devices.append({
                "index": device["index"],
                "name": device["name"],
                "host_api": device["host_api"]
            })
        current_device = None
        if state.audio_manager:
            current_device = state.audio_manager.device_name

        return {
            "devices": input_devices,
            "current": current_device,
        }
    except Exception as e:
        logger.error(f"❌ Audio Device List Error: {e}")
        return {"devices": [], "current": None}

@router.post("/audio/config")
async def update_audio_config(request: UnifiedAudioConfig):
    state = get_stt_runtime_state()
    if not state.audio_manager:
         raise HTTPException(status_code=503, detail="Audio System not initialized")

    audio_config = app_settings.audio
    changed_audio_config = False

    if request.device_name:
        state.audio_manager.switch_device(request.device_name)

    if (
        request.vad_aggressiveness is not None
        or request.speech_start_threshold is not None
        or request.speech_end_threshold is not None
        or request.min_speech_frames is not None
    ):
        state.audio_manager.update_params(
            start_threshold=request.speech_start_threshold,
            end_threshold=request.speech_end_threshold,
            min_frames=request.min_speech_frames,
            aggressiveness=request.vad_aggressiveness,
        )

    for key in (
        "enable_voiceprint_filter",
        "voiceprint_threshold",
        "voiceprint_profile",
    ):
        value = getattr(request, key)
        if value is not None:
            setattr(audio_config, key, value)
            changed_audio_config = True

    if changed_audio_config:
        app_settings.save()
        voiceprint_filter = state.voiceprint_manager
        if voiceprint_filter:
            await voiceprint_filter.refresh_profiles(force=True)

    return {
        "status": "updated",
        "current": state.audio_manager.device_name,
        "config": request.dict(exclude_none=True),
    }

@router.get("/voiceprint/status")
async def get_voiceprint_status():
    state = get_stt_runtime_state()
    audio_config = app_settings.audio
    if not state.voiceprint_manager:
        return {
            "enabled": audio_config.enable_voiceprint_filter,
            "loaded": False,
            "threshold": audio_config.voiceprint_threshold,
            "profile": audio_config.voiceprint_profile,
            "profile_loaded": False,
        }
    return {
        "enabled": audio_config.enable_voiceprint_filter,
        "loaded": True,
        "threshold": audio_config.voiceprint_threshold,
        "profile": audio_config.voiceprint_profile,
        "profile_loaded": audio_config.voiceprint_profile in state.voiceprint_manager.profiles,
    }

@router.get("/audio/status")
async def get_audio_status():
    state = get_stt_runtime_state()
    if not state.audio_manager: return {"status": "uninitialized"}
    status = state.audio_manager.get_status()
    status.update({
        "speech_start_threshold": state.audio_manager.speech_start_threshold,
        "speech_end_threshold": state.audio_manager.speech_end_threshold,
        "vad_aggressiveness": state.audio_manager.vad_aggressiveness,
        "min_speech_frames": state.audio_manager.min_speech_frames
    })
    return status

# --- WebSocket ---

@router.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await SttWebSocketHub(get_stt_runtime_state()).handle(websocket)

# ========== [Scheme C] Internal Endpoints for Main Process Proxy ==========

@router.post("/internal/voiceprint/generate-embedding")
async def generate_voiceprint_embedding(audio: UploadFile = File(...), request: Request = None):
    # Security: Localhost only
    if request and request.client and request.client.host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Internal endpoint: localhost only")
    
    try:
        return await VoiceprintEmbeddingService(get_stt_runtime_state()).generate(audio)
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
