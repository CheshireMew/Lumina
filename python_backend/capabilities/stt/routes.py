
import logging
import asyncio
import queue
from typing import Any, Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, BackgroundTasks, Request, File, UploadFile
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from routers.deps import get_stt_service
from . import globals as stt_globals
from .globals import audio_manager, active_websockets, message_queue
from app_config import config as app_settings
from core.protocols.lipp import LippProtocol, LippLifecycleRequest, LippConfigRequest

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
    speech_start_threshold: Optional[float] = None
    speech_end_threshold: Optional[float] = None
    min_speech_frames: Optional[int] = None

# --- LIPP Handlers ---

async def stt_lifecycle_handler(payload: LippLifecycleRequest):
    """LIPP Lifecycle Implementation"""
    stt_manager = stt_globals.stt_manager
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
    stt_manager = stt_globals.stt_manager
    
    logger.info(f"⚙️ [LIPP] Config: {payload.target_id} -> {payload.key}={payload.value}")
    
    config = stt_manager.update_driver_config(payload.target_id, payload.key, payload.value)

    # Hot Reload
    if payload.key in ["model_size", "fw_model_size"]:
        await stt_manager.switch_model_background(payload.value)

    return {"config": config}

async def stt_health_check():
    from core.protocols.lipp import LippHealthResponse
    status = "ok"
    details = {}
    if audio_manager:
        if not audio_manager.is_running and len(active_websockets) > 0:
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
             "type": "plugin",
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
        "vad_status": "active" if audio_manager and audio_manager.is_running else "idle"
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

    if audio_manager and audio_manager.is_running:
        audio_manager.stop()
        
    await stt_manager.switch_model_background(target)
    # [Config] Local Update for runtime consistency
    app_settings.set_selected_provider("stt", stt_manager.active_driver_id)

    if audio_manager:
        background_tasks.add_task(audio_manager.start)

    # [Scheme D] Active Notification to Main
    # Main process will handle persistence if needed via its own controller logic
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()

    return {"status": "ok", "active_model": stt_manager.active_driver_id}

# --- Audio Config ---

@router.get("/audio/devices")
async def list_audio_devices():
    from . import globals as stt_globals
    from services.managers.audio_devices import AudioDeviceSelector

    try:
        selector = (
            stt_globals.audio_manager.device_selector
            if stt_globals.audio_manager
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
        if stt_globals.audio_manager:
            current_device = stt_globals.audio_manager.device_name

        return {
            "devices": input_devices,
            "current": current_device,
        }
    except Exception as e:
        logger.error(f"❌ Audio Device List Error: {e}")
        return {"devices": [], "current": None}

@router.post("/audio/config")
async def update_audio_config(request: UnifiedAudioConfig):
    if not audio_manager:
         raise HTTPException(status_code=503, detail="Audio System not initialized")

    if request.device_name:
        audio_manager.switch_device(request.device_name)

    if (
        request.speech_start_threshold is not None
        or request.speech_end_threshold is not None
        or request.min_speech_frames is not None
    ):
        audio_manager.update_params(
            start_threshold=request.speech_start_threshold,
            end_threshold=request.speech_end_threshold,
            min_frames=request.min_speech_frames,
        )

    return {
        "status": "updated",
        "current": audio_manager.device_name,
        "config": request.dict(exclude_none=True),
    }

@router.get("/voiceprint/status")
async def get_voiceprint_status():
    from . import globals as stt_globals
    if not stt_globals.voiceprint_manager:
        return {
            "enabled": False,
            "loaded": False,
            "threshold": getattr(audio_manager, "voiceprint_threshold", 0.6),
            "profile": "default",
            "profile_loaded": False,
        }
    return {
        "enabled": True,
        "loaded": True,
        "threshold": getattr(audio_manager, 'voiceprint_threshold', 0.6),
        "profile": getattr(stt_globals.voiceprint_manager, 'current_profile', None) or "default",
        "profile_loaded": True
    }

@router.get("/audio/status")
async def get_audio_status():
    if not audio_manager: return {"status": "uninitialized"}
    status = audio_manager.get_status()
    status.update({
        "speech_start_threshold": audio_manager.speech_start_threshold,
        "speech_end_threshold": audio_manager.speech_end_threshold,
        "min_speech_frames": audio_manager.min_speech_frames
    })
    return status

# --- WebSocket ---

@router.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    token = websocket.query_params.get("token")
    if not token:
        await websocket.close(code=1008, reason="Missing stream token")
        return

    try:
        from security.tokens import TokenManager

        payload = TokenManager.verify_token(token, expected_scope="worker_access")
        worker_id = getattr(websocket.app.state, "worker_id", None)
        if not payload or (worker_id and payload.get("sub") != worker_id):
            await websocket.close(code=1008, reason="Invalid stream token")
            return
    except Exception:
        await websocket.close(code=1008, reason="Invalid stream token")
        return

    await websocket.accept()
    import uuid
    connection_id = str(uuid.uuid4())
    active_websockets[connection_id] = websocket
    
    if len(active_websockets) == 1 and audio_manager:
        if not audio_manager.is_running:
            audio_manager.start()
            while not message_queue.empty():
                try: message_queue.get_nowait()
                except queue.Empty: break
                except Exception as e: 
                    logger.debug(f"Queue drain error (ignorable): {e}")
                    break

    async def sender_task():
        try:
            while True:
                if not message_queue.empty():
                    msg = message_queue.get_nowait()
                    await websocket.send_json(msg)
                await asyncio.sleep(0.02)
        except WebSocketDisconnect: pass
        except Exception as e: logger.error(f"WS Sender Error: {e}")

    async def receiver_task():
        try:
            while True:
                try: await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    if websocket.client_state == 3: raise WebSocketDisconnect()
                    continue
        except WebSocketDisconnect: pass

    try:
        sender = asyncio.create_task(sender_task())
        receiver = asyncio.create_task(receiver_task())
        done, pending = await asyncio.wait([sender, receiver], return_when=asyncio.FIRST_COMPLETED)
        for task in pending: task.cancel()
    finally:
        if connection_id in active_websockets: del active_websockets[connection_id]
        if len(active_websockets) == 0 and audio_manager and audio_manager.is_running:
             audio_manager.stop()

# ========== [Scheme C] Internal Endpoints for Main Process Proxy ==========

@router.post("/internal/voiceprint/generate-embedding")
async def generate_voiceprint_embedding(audio: UploadFile = File(...), request: Request = None):
    # Security: Localhost only
    if request and request.client and request.client.host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Internal endpoint: localhost only")
    
    from . import globals as stt_globals
    import soundfile as sf
    import tempfile
    import os
    import base64
    import asyncio
    
    vp_manager = stt_globals.voiceprint_manager
    if not vp_manager:
        raise HTTPException(status_code=503, detail="Voiceprint driver not loaded")
    await vp_manager.ensure_driver_loaded()
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        audio_data, sr = sf.read(tmp_path)
        if audio_data.ndim > 1: audio_data = audio_data[:, 0]
        
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(None, vp_manager.driver.extract_embedding, audio_data, sr)
        
        if embedding is None or embedding.size == 0: raise HTTPException(500, "Failed to extract embedding")
        
        import numpy as np
        embedding_b64 = base64.b64encode(embedding.astype(np.float32).tobytes()).decode('utf-8')
        return {"embedding": embedding_b64, "dims": len(embedding)}
        
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path): os.remove(tmp_path)
