
import logging
import asyncio
import queue
from typing import Any, Dict, Optional, List
from fastapi import APIRouter, Depends, HTTPException, WebSocket, BackgroundTasks, Request, File, UploadFile
from pydantic import BaseModel
from starlette.websockets import WebSocketDisconnect

from routers.deps import get_stt_service
from routers.deps import get_stt_service
import services.stt.globals as stt_globals
from app_config import config as app_settings

logger = logging.getLogger("STTRouter")

router = APIRouter()

# Helper Accessors Removed - Use stt_globals directly


# --- Data Models ---
# ... (Keep existing models)

# [NOTE] Since I cannot easily replace valid properties with MultiReplace in one go without context,
# I will use a clever trick: I will just keep the variable names but make them point to the dynamic lookup?
# No, module level properties are tricky in Python < 3.7 (though we are 3.11).
# Better: I will just do a mass replace of "audio_manager" -> "stt_globals.audio_manager" in the file?
# That's risky with find/replace.
# Safe bet: Redefine the variables at module level? 
# "audio_manager = None" -> "stt_globals.audio_manager"
# No, that runs once.
# I must update the call sites.

# Plan B:
# 1. Update IMPORTS.
# 2. Add a `get_audio_manager()` helper and replace usages.

# Actually, I'll just change the import line and then use `stt_globals.audio_manager` in the endpoint logic.
# But replacing "if not audio_manager" across the whole file is annoying.
# FASTEST FIX:
# Don't change the variable name `audio_manager`.
# Instead, make `audio_manager` a proxy object? Too complex.
# Just change the call sites in `list_audio_devices` and `update_audio_config` and `websocket_endpoint`.

# Let's replace the import first and define a local valid alias if possible, or just fix usages.


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
        "current_model": stt_manager.current_model_name, # Frontend expects current_model
        "engine_type": stt_manager.engine_type,          # Frontend expects engine_type
        "loading_status": stt_manager.loading_status,    # Frontend expects loading_status
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
    if hasattr(request.app.state, "reporter"):
        await request.app.state.reporter.force_report()
        logger.info("🚀 Force-pushed switch result to Registry")

    return {"status": "ok", "active_model": stt_manager.active_driver_id}

# --- Audio Config ---

@router.get("/audio/devices")
async def list_audio_devices():
    import sounddevice as sd
    try:
        devices = sd.query_devices()
        input_devices = []
        current_device_name = None
        
        # Try to get looking at audio_manager if initialized
        if stt_globals.audio_manager and hasattr(stt_globals.audio_manager, 'device_index'):
             # This is tricky because audio_manager stores index, but frontend wants name or we return index.
             # Let's see what sd.query_devices() returns for default.
             pass

        # [Filter] Blocklist for System Loopbacks / Output Devices pretending to be Inputs
        IGNORE_KEYWORDS = [
            'Microsoft 声音映射器', 'Microsoft Sound Mapper', 
            '主声音捕获驱动程序', 'Primary Sound Capture Driver', 
            '扬声器', 'Speaker', 
            'Stereo Mix', '立体声混音',
            'Output'
        ]

        for i, d in enumerate(devices):
            if d['max_input_channels'] > 0:
                name = d['name']
                # Filter out ignored
                if any(k in name for k in IGNORE_KEYWORDS):
                    continue
                    
                input_devices.append({
                    "index": i, 
                    "name": name, 
                    "host_api": d['hostapi']
                })
        
        # Simple heuristic for current device if audio_manager is active
        return {"devices": stt_globals.audio_manager.list_devices(), "current": stt_globals.audio_manager.device_name}
    except Exception as e:
        logger.error(f"Audio Device List Error: {e}")
        return {"devices": [], "current": None}

@router.post("/audio/config")
async def update_audio_config(request: UnifiedAudioConfig):
    """Update Audio / VAD / Voiceprint settings"""
    if not stt_globals.audio_manager:
        raise HTTPException(status_code=503, detail="Audio System not initialized")

    # 1. Device
    if request.device_name:
        # TODO: Implement device switch in AudioManager
        logger.info(f"Target Device: {request.device_name} (Not implemented hot-switch yet)")
        
    # 2. VAD Params
    if request.speech_start_threshold is not None:
        stt_globals.audio_manager.speech_start_threshold = request.speech_start_threshold
    
    if request.speech_end_threshold is not None:
         stt_globals.audio_manager.speech_end_threshold = request.speech_end_threshold
         
    if request.min_speech_frames is not None:
        stt_globals.audio_manager.min_speech_frames = request.min_speech_frames

    # 3. Voiceprint
    # [Architecture Simplification] Disabled Voiceprint Config
    # if request.enable_voiceprint_filter is not None:
    #     audio_manager.enable_voiceprint = request.enable_voiceprint_filter
    #     if request.enable_voiceprint_filter and not audio_manager.voiceprint_manager:
    #         logger.warning("Enabled Voiceprint but no Manager loaded!")
    #         
    # if request.voiceprint_threshold is not None:
    #     audio_manager.voiceprint_threshold = request.voiceprint_threshold

    # Profile Loading
    # if request.voiceprint_profile and audio_manager.voiceprint_manager:
    #     success = await audio_manager.voiceprint_manager.load_profile(request.voiceprint_profile)
    #     if not success:
    #          logger.warning(f"Failed to load profile: {request.voiceprint_profile}")

    return {"status": "updated", "config": request.dict(exclude_none=True)}

@router.get("/status/voiceprint")
@router.get("/voiceprint/status") # Alias for frontend compatibility
async def get_voiceprint_status():
    from services.stt.globals import voiceprint_manager # Dynamic import to ensure latest
    
    if not voiceprint_manager:
        return {"active": False, "loaded": False}
        
    return {
        "active": True,
        "loaded": True,
        "threshold": getattr(stt_globals.audio_manager, 'voiceprint_threshold', 0.6),
        "profile": "default", # TODO: Track current profile
        "profile_loaded": True
    }

@router.get("/audio/status")
async def get_audio_status():
    if not stt_globals.audio_manager: return {"status": "uninitialized"}
    status = stt_globals.audio_manager.get_status()
    # Ensure VAD params are included
    status.update({
        "speech_start_threshold": stt_globals.audio_manager.speech_start_threshold,
        "speech_end_threshold": stt_globals.audio_manager.speech_end_threshold,
        "min_speech_frames": stt_globals.audio_manager.min_speech_frames
    })
    return status

# --- WebSocket ---

@router.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import uuid
    connection_id = str(uuid.uuid4())
    stt_globals.active_websockets[connection_id] = websocket
    logger.info(f"Client connected: {connection_id} (Total: {len(stt_globals.active_websockets)})")
    
    # Auto-Start Audio Manager if first client
    if len(stt_globals.active_websockets) == 1 and stt_globals.audio_manager:
        if not stt_globals.audio_manager.is_running:
            logger.info("[Auto-Start] Starting AudioManager (First Client)")
            # Run in executor to avoid blocking WS loop? 
            # start() creates threads, so it is non-blocking usually.
            stt_globals.audio_manager.start()
            
            # Clear queue
            while not stt_globals.message_queue.empty():
                try: stt_globals.message_queue.get_nowait()
                except queue.Empty: break
                except Exception: pass

    async def sender_task():
        try:
            while True:
                # Poll queue
                if not stt_globals.message_queue.empty():
                    msg = stt_globals.message_queue.get_nowait()
                    await websocket.send_json(msg)
                await asyncio.sleep(0.02)
        except WebSocketDisconnect:
            logger.info(f"WS Sender Disconnect: {connection_id}")
        except Exception as e:
            logger.error(f"WS Sender Error: {e}")

    async def receiver_task():
        try:
            while True:
                # Keep connection alive by reading (and ignoring) input
                # Use timeout to detect zombie connections (e.g. 30s)
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    # No data for 30s. Client might be silent or dead.
                    # We could send a ping frame, or just ignore if we expect silence.
                    # But for robustness, if we expect "keep-alive" traffic, we should reconnect.
                    # Since we don't have a protocol demanding client pings, let's just log and continue?
                    # Or relying on TCP keepalive?
                    # Better: Check client state.
                    if websocket.client_state == 3: # Disconnected
                         raise WebSocketDisconnect()
                    # Just loop to check connection_state
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
        if connection_id in stt_globals.active_websockets:
            del stt_globals.active_websockets[connection_id]
        
        # Auto-Stop
        if len(stt_globals.active_websockets) == 0 and stt_globals.audio_manager and stt_globals.audio_manager.is_running:
             logger.info("[Auto-Stop] Stopping AudioManager (No Clients)")
             stt_globals.audio_manager.stop()

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
    
    # 2. Target: Voiceprint / Audio (Global)
    # [Architecture Simplification] Disabled Voiceprint Config
    # if req.id == "system.voiceprint" or req.id == "voiceprint":
    #     from services.stt.globals import audio_manager
    #     if req.key == "voiceprint_threshold" and audio_manager:
    #         audio_manager.voiceprint_threshold = float(req.value)
    #         return {"status": "ok", "threshold": audio_manager.voiceprint_threshold}

    return {"status": "error", "message": f"Plugin {req.id} not found on this worker"}

@router.post("/plugins/load")
async def load_plugins(req: PluginLoadRequest, request: Request, background_tasks: BackgroundTasks, stt_manager: Any = Depends(get_stt_service)):
    # ... existing load_plugins logic ...
    """
    Refactored Load Endpoint
    Called by SystemPluginManager to load plugins on this worker.
    """
    from services.plugins.loader import PluginLoader
    from core.interfaces.driver import BaseSTTDriver
    import services.stt.globals as stt_globals

    loaded = []
    
    for manifest_path in req.manifests:
        try:
            # 1. Load Instance
            plugin = PluginLoader.load_from_file(manifest_path)
            if not plugin:
                logger.error(f"Failed to load plugin from {manifest_path}")
                continue
                
            # 2. Register based on Type
            
            # Case A: STT Driver
            if isinstance(plugin, BaseSTTDriver):
                stt_manager.register_driver(plugin)
                loaded.append(plugin.id)
                
            # Case B: Voiceprint Manager (Special)
            # [Architecture Simplification] Disable Voiceprint Loading
            # elif plugin.id == "system.voiceprint":
            #     stt_globals.voiceprint_manager = plugin
            #     if stt_globals.audio_manager:
            #          stt_globals.audio_manager.voiceprint_manager = plugin
            #          # Sync config enablement
            #          from app_config import config
            #          stt_globals.audio_manager.enable_voiceprint = config.audio.enable_voiceprint_filter
                
            #     # Init Context
            #     from core.api.context import LuminaContext
            #     from core.api.sandboxed_context import SandboxedContext
            #     from services.container import services
                
            #     if not getattr(services, 'config', None): 
            #         from app_config import config
            #         services.config = config
                
            #     # [Security] Determine Context Type based on Manifest Permissions
            #     manifest = getattr(plugin, '_manifest', None)
            #     perms = getattr(manifest, 'permissions', []) if manifest else []
                
            #     # [Fix] Retrieve RouterManager from App State
            #     router_manager = getattr(request.app.state, "router_manager", None)

            #     if "unsafe_trust" in perms:
            #         ctx = LuminaContext(container=services, plugin_id=plugin.id, router_manager=router_manager)
            #         logger.info(f"🔓 Granted Full Context to {plugin.id} (unsafe_trust)")
            #     else:
            #         ctx = SandboxedContext(container=services, plugin_id=plugin.id, permissions=perms, router_manager=router_manager)
            #         logger.info(f"🛡️ Granted Sandboxed Context to {plugin.id} (Perms: {len(perms)})")
                
            #     if hasattr(plugin, 'initialize'):
            #         import inspect
            #         if inspect.iscoroutinefunction(plugin.initialize):
            #             await plugin.initialize(ctx)
            #         else:
            #             plugin.initialize(ctx)
                
            #     loaded.append(plugin.id)
            #     logger.info(f"✅ Voiceprint Manager Loaded from {manifest_path}")

            else:
                logger.warning(f"Unknown plugin type loaded on STT Server: {plugin.id} ({type(plugin)})")
                # Keep it? For now just log.

        except Exception as e:
            logger.error(f"Error loading {manifest_path}: {e}", exc_info=True)
            
    # [Scheme D] Active Event Emission
    # Notify Main Registry immediately that we have new capabilities
    # Notify Main Registry immediately that we have new capabilities
    if hasattr(request.app.state, "reporter"):
        # Assuming async WorkerStatusReporter as verified
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
             
             # 2. Check Voiceprint
             # [Architecture Simplification] Switch Disabled
             # from services.stt.globals import voiceprint_manager, audio_manager
             # if voiceprint_manager and voiceprint_manager.id == p_id:
             #      logger.warning("🛑 Voiceprint Manager disabled! Detaching...")
             #      import services.stt.globals as stt_globals
             #      stt_globals.voiceprint_manager = None
                  
             #      if audio_manager:
             #          audio_manager.voiceprint_manager = None
             #          audio_manager.enable_voiceprint = False

        elif p_type == "enabled":
             app_settings.load_configs()
             target = app_settings.stt.provider
             
             # Driver Check
             if target == p_id and stt_manager:
                  logger.info(f"🟢 Configured driver {p_id} enabled. Loading...")
                  await stt_manager.activate(p_id)
             
             # Voiceprint Check
             # [Architecture Simplification] Switch Disabled
             # if p_id == "system.voiceprint" or p_id == "voiceprint":
             #      logger.info("🎤 Voiceprint enable requested. Hot-loading...")
             #      try:
             #          import os
             #          from services.plugins.loader import PluginLoader
             #          from core.api.context import LuminaContext
             #          from services.container import services
             #          import services.stt.globals as stt_globals
                      
             #          # Back to root -> plugins/system/voiceprint
             #          base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
             #          manifest_path = os.path.join(base_dir, "plugins", "extensions", "voiceprint", "manifest.yaml")
                      
             #          if os.path.exists(manifest_path):
             #              vp_mgr = PluginLoader.load_from_file(manifest_path)
             #              if vp_mgr:
             #                  stt_globals.voiceprint_manager = vp_mgr
             #                  if stt_globals.audio_manager:
             #                       stt_globals.audio_manager.voiceprint_manager = vp_mgr
             #                       stt_globals.audio_manager.enable_voiceprint = True
                              
             #                  # Init
             #                  rm = getattr(request.app.state, "router_manager", None)
             #                  ctx = LuminaContext(container=services, plugin_id="system.voiceprint", router_manager=rm)
             #                  if hasattr(vp_mgr, 'initialize'):
             #                      import inspect
             #                      if inspect.iscoroutinefunction(vp_mgr.initialize):
             #                          await vp_mgr.initialize(ctx)
             #                      else:
             #                          vp_mgr.initialize(ctx)
                              
             #                  if hasattr(vp_mgr, 'ensure_driver_loaded'):
             #                      await vp_mgr.ensure_driver_loaded()
                                  
             #                  logger.info(f"✅ Voiceprint Service Hot-Loaded & Activated")
             #              else:
             #                  logger.error("❌ Loader returned None")
             #          else:
             #              logger.error(f"❌ Manifest missing: {manifest_path}")
                          
             #      except Exception as e:
             #          logger.error(f"Hot-load error: {e}", exc_info=True)

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
    Called by Main Process /plugins/voiceprint/upload.
    Localhost-only, not exposed to frontend.
    """
    # Security: Localhost only
    if request and request.client and request.client.host not in ["127.0.0.1", "::1", "localhost"]:
        raise HTTPException(status_code=403, detail="Internal endpoint: localhost only")
    
    import services.stt.globals as stt_globals
    import soundfile as sf
    import tempfile
    import os
    import base64
    import asyncio
    
    vp_manager = stt_globals.voiceprint_manager
    if not vp_manager:
        raise HTTPException(status_code=503, detail="Voiceprint service not available on this worker")
    
    if not hasattr(vp_manager, 'driver') or not vp_manager.driver:
        raise HTTPException(status_code=503, detail="Voiceprint driver not loaded")
    
    tmp_path = None
    try:
        # Save uploaded audio to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as tmp:
            content = await audio.read()
            tmp.write(content)
            tmp_path = tmp.name
        
        # Load audio
        audio_data, sr = sf.read(tmp_path)
        if audio_data.ndim > 1:
            audio_data = audio_data[:, 0]  # Mono
        
        # Generate embedding (CPU-bound, offload to executor)
        loop = asyncio.get_running_loop()
        embedding = await loop.run_in_executor(
            None,
            vp_manager.driver.extract_embedding,
            audio_data,
            sr
        )
        
        if embedding is None or embedding.size == 0:
            raise HTTPException(status_code=500, detail="Failed to extract embedding from audio")
        
        # Encode as base64 for transport
        import numpy as np
        embedding_bytes = embedding.astype(np.float32).tobytes()
        embedding_b64 = base64.b64encode(embedding_bytes).decode('utf-8')
        
        logger.info(f"✅ Generated voiceprint embedding: {len(embedding)} dims")
        return {"embedding": embedding_b64, "dims": len(embedding)}
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Embedding generation failed: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        if tmp_path and os.path.exists(tmp_path):
            os.remove(tmp_path)

