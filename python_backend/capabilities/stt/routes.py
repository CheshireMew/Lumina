
import logging
import asyncio
import queue
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, BackgroundTasks, Request, File, UploadFile
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from routers.deps import get_stt_service
from .globals import audio_manager, active_websockets, message_queue
from app_config import config as app_settings

logger = logging.getLogger("STTRouter")

router = APIRouter()

# --- Data Models ---

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

class PluginLoadRequest(BaseModel):
    manifests: List[str]

class LifecyclePayload(BaseModel):
    type: str # 'enabled' | 'disabled'
    plugin_id: str
    config: Optional[Dict] = None

class PluginConfigRequest(BaseModel):
    id: str
    key: str
    value: Any


# --- Endpoints ---

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
    for pid, drv in stt_manager.drivers.items():
         # Avoid duplicates if they map to above engines
         if pid in ["driver.stt.sensevoice", "driver.stt.whisper"]: continue
         
         models.append({
             "id": pid,
             "name": drv.name,
             "type": "plugin",
             "description": drv.description,
             "active": (stt_manager.active_driver_id == pid)
         })

    return {
        "active_model": stt_manager.current_model_name,
        "engine": stt_manager.engine_type,
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
    
    # Validation
    valid = False
    target = payload.model_name
    
    # Check drivers
    if target in stt_manager.drivers:
        valid = True
    elif target in ["faster-whisper", "sense-voice"]: # Legacy aliases
        valid = True
        
    if not valid:
        raise HTTPException(status_code=400, detail=f"Unknown model/driver: {target}")

    # Stop Audio First
    if audio_manager and audio_manager.is_running:
        logger.info("Pausing Audio for Switch...")
        audio_manager.stop()
        
    # Execute Switch
    await stt_manager.switch_model_background(target)

    # Save Config
    app_settings.stt.provider = stt_manager.active_driver_id
    app_settings.save()

    # Restart Audio
    if audio_manager:
        logger.info("Resuming Audio...")
        background_tasks.add_task(audio_manager.start)

    # [Scheme D] Active Notification for SSOT Reconciliation
    # Reporter is injected into app.state by generic_worker
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()
        logger.info("🚀 Force-pushed switch result to Registry")

    return {"status": "ok", "active_model": stt_manager.active_driver_id}

# --- Audio Config ---

@router.get("/audio/devices")
async def list_audio_devices():
    import sounddevice as sd
    logger.info("🎤 [Debug] Querying Audio Devices...")
    try:
        devices = sd.query_devices()
        logger.info(f"🎤 [Debug] Raw Device Count: {len(devices)}")
        
        input_devices = []
        for i, d in enumerate(devices):
            # logger.info(f"   Device {i}: {d['name']} (In: {d['max_input_channels']})")
            if d['max_input_channels'] > 0:
                input_devices.append({
                    "index": i, 
                    "name": d['name'], 
                    "host_api": d['hostapi']
                })
        
        logger.info(f"🎤 [Debug] Filtered Input Devices: {len(input_devices)}")
        return input_devices
    except Exception as e:
        logger.error(f"❌ Audio Device List Error: {e}", exc_info=True)
        return []

@router.post("/config/audio")
async def update_audio_config(request: UnifiedAudioConfig):
    """Update Audio / VAD / Voiceprint settings"""
    if not audio_manager:
        raise HTTPException(status_code=503, detail="Audio System not initialized")

    # 1. Device
    if request.device_name:
        success = audio_manager.switch_device(request.device_name)
        logger.info(f"🔄 Device switch: {request.device_name} -> {'OK' if success else 'FAIL'}")
        
    # 2. VAD Params
    if request.speech_start_threshold is not None:
        audio_manager.speech_start_threshold = request.speech_start_threshold
    
    if request.speech_end_threshold is not None:
         audio_manager.speech_end_threshold = request.speech_end_threshold
         
    if request.min_speech_frames is not None:
        audio_manager.min_speech_frames = request.min_speech_frames

    return {"status": "updated", "config": request.dict(exclude_none=True)}

@router.get("/status/voiceprint")
@router.get("/voiceprint/status") # Alias for frontend compatibility
async def get_voiceprint_status():
    from . import globals as stt_globals # Dynamic import
    
    if not stt_globals.voiceprint_manager:
        return {"active": False, "loaded": False}
        
    return {
        "active": True,
        "loaded": True,
        "threshold": getattr(audio_manager, 'voiceprint_threshold', 0.6),
        "profile": getattr(stt_globals.voiceprint_manager, 'current_profile', None) or "default",
        "profile_loaded": True
    }

@router.get("/audio/status")
async def get_audio_status():
    if not audio_manager: return {"status": "uninitialized"}
    status = audio_manager.get_status()
    # Ensure VAD params are included
    status.update({
        "speech_start_threshold": audio_manager.speech_start_threshold,
        "speech_end_threshold": audio_manager.speech_end_threshold,
        "min_speech_frames": audio_manager.min_speech_frames
    })
    return status

# --- WebSocket ---

@router.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import uuid
    connection_id = str(uuid.uuid4())
    active_websockets[connection_id] = websocket
    logger.info(f"Client connected: {connection_id} (Total: {len(active_websockets)})")
    
    # Auto-Start Audio Manager if first client
    if len(active_websockets) == 1 and audio_manager:
        if not audio_manager.is_running:
            logger.info("[Auto-Start] Starting AudioManager (First Client)")
            audio_manager.start()
            
            # Clear queue
            while not message_queue.empty():
                try: message_queue.get_nowait()
                except queue.Empty: break
                except Exception: pass

    async def sender_task():
        try:
            while True:
                # Poll queue
                if not message_queue.empty():
                    msg = message_queue.get_nowait()
                    await websocket.send_json(msg)
                await asyncio.sleep(0.02)
        except WebSocketDisconnect:
            logger.info(f"WS Sender Disconnect: {connection_id}")
        except Exception as e:
            logger.error(f"WS Sender Error: {e}")

    async def receiver_task():
        try:
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    if websocket.client_state == 3: # Disconnected
                         raise WebSocketDisconnect()
                    continue
        except WebSocketDisconnect:
            logger.info(f"WS Receiver Disconnect: {connection_id}")

    try:
        # Run both tasks
        sender = asyncio.create_task(sender_task())
        receiver = asyncio.create_task(receiver_task())
        done, pending = await asyncio.wait(
            [sender, receiver], 
            return_when=asyncio.FIRST_COMPLETED
        )
        for task in pending: task.cancel()
        
    except Exception as e:
        logger.error(f"WS Connection Error: {e}")
    finally:
        # Cleanup
        if connection_id in active_websockets:
            del active_websockets[connection_id]
        
        # Auto-Stop
        if len(active_websockets) == 0 and audio_manager and audio_manager.is_running:
             logger.info("[Auto-Stop] Stopping AudioManager (No Clients)")
             audio_manager.stop()

# --- Lifecycle Endpoints ---

@router.post("/plugins/config")
async def update_plugin_config(req: PluginConfigRequest, stt_manager: Any = Depends(get_stt_service)):
    """Unified Config Endpoint for Workers"""
    logger.info(f"⚙️ [Worker Config] {req.id} -> {req.key}={req.value}")
    
    # 1. Target: STT Driver
    if req.id in stt_manager.drivers:
        driver = stt_manager.drivers[req.id]
        driver.config[req.key] = req.value
        
        # Trigger hot-reload if it's a model switch
        if req.key == "model_size" or req.key == "fw_model_size":
            await stt_manager.switch_model_background(req.value)
            
        return {"status": "ok", "config": driver.config}
    
    return {"status": "error", "message": f"Plugin {req.id} not found on this worker"}

@router.post("/plugins/load")
async def load_plugins(req: PluginLoadRequest, request: Request, background_tasks: BackgroundTasks, stt_manager: Any = Depends(get_stt_service)):
    """
    Refactored Load Endpoint
    Called by SystemPluginManager to load plugins on this worker.
    """
    from services.plugins.loader import PluginLoader
    from core.interfaces.driver import BaseSTTDriver
    import capabilities.stt.globals as stt_globals

    loaded = []
    
    for manifest_path in req.manifests:
        try:
            # 1. Load Instance
            plugin = PluginLoader.load_from_file(manifest_path)
            if not plugin:
                logger.error(f"Failed to load plugin from {manifest_path}")
                continue
                
            # 2. Register based on Type
            if isinstance(plugin, BaseSTTDriver):
                stt_manager.register_driver(plugin)
                loaded.append(plugin.id)
            else:
                logger.warning(f"Unknown plugin type loaded on STT Server: {plugin.id} ({type(plugin)})")

        except Exception as e:
            logger.error(f"Error loading {manifest_path}: {e}", exc_info=True)
            
    # [Scheme D] Active Event Emission
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()
        logger.info("🚀 Force-pushed new capabilities to Registry")

    return {"status": "ok", "loaded": loaded}

@router.post("/system/lifecycle")
async def handle_lifecycle(payload: LifecyclePayload, request: Request, stt_manager: Any = Depends(get_stt_service)):
    """
    [Scheme D] The 'Shout' Receiver.
    """
    # [Security] Localhost only
    if request.client.host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Access Denied")
    logger.info(f"📢 [Lifecycle] Received: {payload.type} -> {payload.plugin_id}")
    p_id = payload.plugin_id
    p_type = payload.type
    
    try:
        if p_type == "disabled":
             # 1. Check STT Driver
             if stt_manager and p_id in stt_manager.drivers:
                 if stt_manager.active_driver_id == p_id:
                      logger.info(f"🛑 Active Driver {p_id} disabled. Unloading...")
                      await stt_manager.unload_active_driver()
             
        elif p_type == "enabled":
             app_settings.load_configs()
             target = app_settings.stt.provider
             
             # Driver Check
             if target == p_id and stt_manager:
                  logger.info(f"🟢 Configured driver {p_id} enabled. Loading...")
                  await stt_manager.activate(p_id)
             
    except Exception as e:
        logger.error(f"Lifecycle Error: {e}")

    # [Scheme D] Immediate Registry Update
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()
        logger.info("🚀 Force-pushed lifecycle result to Registry")

    return {"status": "ok"}


# ========== [Scheme C] Internal Endpoints for Main Process Proxy ==========

@router.post("/internal/voiceprint/generate-embedding")
async def generate_voiceprint_embedding(audio: UploadFile = File(...), request: Request = None):
    """
    [Scheme C] Internal endpoint for embedding generation.
    """
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
    # ... rest of logic (simplified for readability, keeping core)
    # Actually, legacy voiceprint code was disabled in original file comments.
    # But if enabled, it would be here.
    
    if not vp_manager:
        raise HTTPException(status_code=503, detail="Voiceprint service not available on this worker")
    
    if not hasattr(vp_manager, 'driver') or not vp_manager.driver:
        raise HTTPException(status_code=503, detail="Voiceprint driver not loaded")
    
    tmp_path = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        audio_data, sr = sf.read(tmp_path)
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]  # Mono
        
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            vp_manager.driver.extract_embedding,
            audio_data,
            sr
        )
        
        if embedding is None or embedding.size == 0:
            raise HTTPException(status_code=500, detail="Failed to extract embedding from audio")
        
        import numpy as np
        embedding_bytes = embedding.astype(np.float32).tobytes()
        embedding_b64 = base64.b64encode(embedding_bytes).decode('utf-8')
        
        return {"embedding": embedding_b64, "dims": len(embedding)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)
