"""
FastAPI STT Server with Backend VAD & Multi-Engine Support
支持 Faster-Whisper 和 SenseVoice (Sherpa-ONNX) 引擎切换
使用 AudioManager (sounddevice + webrtcvad) 实现设备隔离和精确VAD
前端通过 WebSocket 接收 VAD 状态和转录结果
"""

import os
import sys
import logging

# [Windows CUDA Fix] Force Python to look for DLLs in the script directory
# This resolves the "cublas64_12.dll not found" error when using local DLLs
if os.name == 'nt':
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        os.add_dll_directory(base_path)
        print(f"[Init] Added DLL directory: {base_path}")
    except Exception as e:
        print(f"[Init] Failed to add DLL directory: {e}")

# --- Custom Logger & Model Manager ---
# --- Custom Logger & Model Manager ---
from logger_setup import setup_logger, request_id_ctx
from model_manager import model_manager
from app_config import config as app_settings


# Initialize Logger (TeeOutput)
logger = setup_logger("stt_server.log")

import numpy as np
import threading
import json
import uuid
import queue
from typing import Optional, Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks, Request
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Engines
from faster_whisper import WhisperModel
from services.audio_manager import AudioManager

# Voiceprint import removed. Loaded dynamically in startup_event.
VoiceprintManager = None

# Driver Imports (Core)
from core.interfaces.driver import BaseSTTDriver
# Drivers are loaded dynamically by STTPluginManager

app = FastAPI(title="Lumina STT Service")

@app.get("/health")
async def health_check():
    return {"status": "ok", "service": "stt"}
@app.middleware("http")
async def request_id_middleware(request: Request, call_next):
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    token = request_id_ctx.set(request_id)
    try:
        response = await call_next(request)
        response.headers["X-Request-ID"] = request_id
        return response
    finally:
        request_id_ctx.reset(token)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Audio Manager Globals ---
audio_manager: Optional[AudioManager] = None
voiceprint_manager = None  # Global voiceprint manager instance
active_websockets: Dict[str, WebSocket] = {} 
message_queue = queue.Queue()

# --- Model Engine Management ---

# MODEL_SIZES moved to plugins.stt.manager
# from plugins.stt.manager import MODEL_SIZES

# from plugins.stt.manager import STTPluginManager, MODEL_SIZES
# But we need services
from services.container import services
# from plugins.stt.manager import WHISPER_MODELS # Dynamic now!

CONFIG_FILE = app_settings.config_root / "stt_config.json"

# Manager removed (Use services.get_stt())
# manager = STTPluginManager()
# engine_manager = manager

@app.on_event("startup")
async def startup_event():
    global audio_manager, voiceprint_manager
    
    # Load model and register drivers (Async)
    # threading.Thread(target=engine_manager.load_model, args=(engine_manager.current_model_name,)).start()
    # await engine_manager.register_drivers() # Handled by Lifecycle
    logger.info("STT Drivers registered via Lifecycle.")
    
    # Load Audio Config from centralized config
    enable_voiceprint = app_settings.audio.enable_voiceprint_filter
    voiceprint_threshold = app_settings.audio.voiceprint_threshold
    voiceprint_profile = app_settings.audio.voiceprint_profile

    
    if enable_voiceprint:
        try:
             # Dynamic Loading based on convention or config
             # We assume standard plugin location unless configured otherwise
             from importlib import import_module
             vp_module = import_module("plugins.system.voiceprint.manager")
             VoiceprintManagerClass = getattr(vp_module, "VoiceprintManager")
             
             logger.info("[Startup] Dynamically loaded VoiceprintManager for STT.")
             
             voiceprint_manager = VoiceprintManagerClass()
             await voiceprint_manager.ensure_driver_loaded()
             
             if voiceprint_profile in voiceprint_manager.profiles:
                 logger.info(f"Voiceprint enabled. Current Profile: {voiceprint_profile}")
             else:
                 logger.warning(f"⚠️ Profile '{voiceprint_profile}' not found in {list(voiceprint_manager.profiles.keys())}. Voiceprint disabled.")
                 enable_voiceprint = False
                 
        except Exception as e:
            logger.error(f"Voiceprint Dynamic Load Failed: {e}")
            enable_voiceprint = False
            voiceprint_manager = None
            
    # Define Audio Callbacks
    # stt_manager = services.get_stt() # Retrieved when needed or global referencing is hard
    # Since audio callbacks need it, and they are defined here...
    stt_manager = services.get_stt()

    def on_speech_start():
        logger.info("[AudioManager] Speech started")
        message_queue.put({"type": "vad_status", "status": "listening"})
    
    def on_speech_end(audio_data: np.ndarray):
        logger.info(f"[AudioManager] Speech ended. Length: {len(audio_data)}")
        message_queue.put({"type": "vad_status", "status": "thinking"})
        
        # Call Transcribe
        try:
            # result = engine_manager.transcribe(audio_data)
            result = stt_manager.transcribe(audio_data)
        
        if stt_manager.model is None:
            logger.warning("STT Model not ready.")
            message_queue.put({"type": "vad_status", "status": "idle"})
            return
        
        try:
            # === ENGINE DISPATCH ===
            print(f"[DEBUG] Engine Type: {stt_manager.engine_type}")
            if stt_manager.engine_type == "sense_voice":
                # SenseVoice Logic - returns (segments, info)
                print(f"[DEBUG] Calling SenseVoice transcribe with {len(audio_data)} samples")
                segments, info = stt_manager.model.transcribe(audio_data)
                print(f"[DEBUG] Transcribe returned. Segments: {len(segments)}")
                
                full_transcript = ""
                for segment in segments:
                    segment_text = segment.text.strip()
                    print(f"[DEBUG] Segment: {segment_text}")
                    if segment_text:
                        full_transcript += segment_text
                
                print(f"[DEBUG] Full Transcript: '{full_transcript}'")
                if full_transcript:
                    # Check for emotion tag from SenseVoice
                    emotion = getattr(info, 'emotion', None)
                    emotion_str = f" [情感:{emotion}]" if emotion else ""
                    logger.info(f"SenseVoice Result: [{info.language}]{emotion_str} {full_transcript}")
                    
                    response = {
                        "type": "transcription",
                        "text": full_transcript,
                        "language": info.language,
                        "is_final": True
                    }
                    if emotion:
                        response["emotion"] = emotion
                    
                    message_queue.put(response)
                else:
                    logger.warning("SenseVoice returned empty text.")
                    print("[DEBUG] SenseVoice returned empty text.")

            elif engine_manager.engine_type == "plugin_asr":
                # Plugin ASR Logic
                import asyncio
                import concurrent.futures
                
                # Plugin expects bytes
                audio_int16 = (audio_data * 32767).astype(np.int16)
                audio_bytes = audio_int16.tobytes()
                
                text = ""
                try:
                    # Run async plugin in sync context safely
                    loop = asyncio.new_event_loop()
                    asyncio.set_event_loop(loop)
                    text = loop.run_until_complete(engine_manager.model.transcribe(audio_bytes, language="zh"))
                    loop.close()
                except Exception as e:
                    logger.error(f"Plugin transcribe failed: {e}")
                
                if text:
                    logger.info(f"Plugin ASR Result: {text}")
                    message_queue.put({
                        "type": "transcription",
                        "text": text,
                        "language": "zh", # Plugin interface should probably return this too
                        "is_final": True
                    })
                else:
                    logger.warning("Plugin ASR returned empty text.")
                    
            elif engine_manager.engine_type in ["paraformer_zh", "paraformer_en"]:
                # Paraformer Logic - returns (segments, info)
                segments, info = engine_manager.model.transcribe(
                    audio_data,
                    beam_size=1
                )
                
                full_transcript = ""
                for segment in segments:
                    segment_text = segment.text.strip()
                    if segment_text:
                        full_transcript += segment_text
                
                if full_transcript:
                    lang_label = "中文" if engine_manager.engine_type == "paraformer_zh" else "English"
                    logger.info(f"Paraformer-{lang_label} Result: [{info.language}] {full_transcript}")
                    message_queue.put({
                        "type": "transcription",
                        "text": full_transcript,
                        "language": info.language,
                        "is_final": True
                    })
                else:
                    logger.warning("Paraformer returned empty text.")
                    
            else:
                # Faster-Whisper Logic
                segments, info = stt_manager.model.transcribe(
                    audio_data,
                    beam_size=1,
                    best_of=1,
                    temperature=0.0,
                    vad_filter=False, # We use external VAD
                    condition_on_previous_text=False,
                    initial_prompt="以下是普通话的句子。This is a Mandarin Chinese sentence."
                )
                
                full_transcript = ""
                for segment in segments:
                    segment_text = segment.text.strip()
                    if segment_text:
                        full_transcript += segment_text
                        message_queue.put({
                            "type": "partial",
                            "text": full_transcript,
                            "segment": segment_text,
                            "is_final": False
                        })
                
                if full_transcript:
                    logger.info(f"Whisper Result: [{info.language}] {full_transcript}")
                    message_queue.put({
                        "type": "transcription",
                        "text": full_transcript,
                        "language": info.language,
                        "is_final": True
                    })
                else:
                    logger.warning("Whisper returned empty text.")

        except Exception as e:
            logger.error(f"Transcription Error: {e}", exc_info=True)
            
        message_queue.put({"type": "vad_status", "status": "idle"})
    
    def on_vad_status_change(status: str):
        message_queue.put({"type": "vad_status", "status": status})
    
    # Initialize AudioManager
    audio_manager = AudioManager(
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_vad_status_change=on_vad_status_change,
        voiceprint_manager=voiceprint_manager,
        enable_voiceprint=enable_voiceprint,
        voiceprint_threshold=voiceprint_threshold,
        aggressiveness=1 if enable_voiceprint else 3
    )
    
    # audio_manager.start() # Defer start to WebSocket connection
    logger.info("AudioManager initialized (Waiting for WS connection to start)")

# --- API Endpoints ---

@app.get("/models/list")
async def get_models():
    """List available STT models and their status"""
    stt_manager = services.get_stt()
    
    # Define available models
    models = []
    
    # Dynamically populate supported models based on loaded drivers
    if hasattr(stt_manager, "drivers"):
        for drv_id, driver in stt_manager.drivers.items():
            
            if hasattr(driver, "supported_models"):
                # Driver explicitly supports multiple sub-models (e.g. FasterWhisper)
                for code, size in driver.supported_models.items():
                     models.append({
                        "name": code,
                        "desc": f"{size} ({driver.name})",
                        "engine": driver.id, # Map back to driver ID? No better to engine type logic?
                                             # Actually stt_server logic expects 'engine' field to match somewhat.
                                             # But let's stick to simple:
                        "is_whisper": driver.id == "faster-whisper", # Heuristic or property?
                        "download_status": "idle" # To be checked later
                     })
            else:
                # Generic Single-Model Driver (e.g., SenseVoice)
                models.append({
                    "name": driver.id,
                    "desc": driver.name,
                    "engine": "plugin_asr", # standardized type
                    "is_whisper": False,
                    "download_status": "completed" # Drivers usually self-manage or are pre-installed
                })
    
    # Check status
    for m in models:
        m["download_status"] = "idle"
        
        # Path checking logic
        if m["engine"] == "sense_voice":
             path = os.path.join(model_manager.base_dir, "sense-voice")
             if os.path.exists(path) and os.listdir(path): m["download_status"] = "completed"
        elif m["engine"] == "paraformer_zh":
             path = os.path.join(model_manager.base_dir, "paraformer-zh")
             if os.path.exists(path) and os.listdir(path): m["download_status"] = "completed"
        elif m["engine"] == "paraformer_en":
             path = os.path.join(model_manager.base_dir, "paraformer-en")
             if os.path.exists(path) and os.listdir(path): m["download_status"] = "completed"
        else:
             # Whisper
             path = os.path.join(model_manager.base_dir, m["name"])
             if os.path.exists(path) and os.listdir(path): m["download_status"] = "completed"

        if stt_manager.loading_status == "loading" and stt_manager.current_model_name == m["name"]:
             m["download_status"] = "downloading"

    return {
        "models": models,
        "current_model": stt_manager.current_model_name,
        "engine_type": stt_manager.engine_type,
        "loading_status": stt_manager.loading_status
    }

class SwitchModelRequest(BaseModel):
    model_name: str

@app.post("/models/switch")
async def switch_model(request: SwitchModelRequest, background_tasks: BackgroundTasks):
    stt_manager = services.get_stt()

    # Allow Whisper models AND Plugin models
    # Dynamic Validation: Check if model_name is a known Whisper size OR a registered driver ID
    
    # [Dynamic Check]
    is_valid = False
    
    # 1. Is it a direct driver ID?
    if request.model_name in stt_manager.drivers:
        is_valid = True
        
    # 2. Is it a sub-model of any driver?
    if not is_valid:
        for drv in stt_manager.drivers.values():
            if hasattr(drv, "supported_models") and request.model_name in drv.supported_models:
                is_valid = True
                break

    if not is_valid:
        logger.warning(f"Switching to unknown model name: {request.model_name}")
        raise HTTPException(status_code=400, detail=f"Invalid model name: {request.model_name}")
    
    # Check if already loading
    if stt_manager.loading_status == "loading":
         raise HTTPException(status_code=409, detail="A model is already loading")

    # Load in background
    background_tasks.add_task(stt_manager.switch_model_background, request.model_name)
    return {"status": "pending", "message": f"Switching to {request.model_name}..."}


# --- Audio Config APIs (Legacy & New) ---

@app.get("/audio/devices")
async def list_audio_devices():
    if not audio_manager:
         raise HTTPException(500, "AudioManager not ready")
    return {"devices": audio_manager.list_devices(), "current": audio_manager.device_name}

class UnifiedAudioConfig(BaseModel):
    # Device & Voiceprint
    device_name: Optional[str] = None
    enable_voiceprint_filter: Optional[bool] = None
    voiceprint_threshold: Optional[float] = None
    voiceprint_profile: Optional[str] = None
    
    # VAD Settings
    speech_start_threshold: Optional[float] = None
    speech_end_threshold: Optional[float] = None
    min_speech_frames: Optional[int] = None

@app.post("/audio/config")
async def update_audio_config(request: UnifiedAudioConfig):
    global audio_manager
    config_path = app_settings.config_root / "audio_config.json"
    
    try:
        # 1. Load existing config
        if config_path.exists():
             with open(config_path, encoding='utf-8-sig') as f:
                 config = json.load(f)
        else:
             config = {}
        
        # 2. Update Config Dict (Persistence)
        if request.device_name is not None:
            config["device_name"] = request.device_name
            
        # Voiceprint
        if request.enable_voiceprint_filter is not None:
            config["enable_voiceprint_filter"] = request.enable_voiceprint_filter
        if request.voiceprint_threshold is not None:
            config["voiceprint_threshold"] = request.voiceprint_threshold
        if request.voiceprint_profile is not None:
            config["voiceprint_profile"] = request.voiceprint_profile
            
        # VAD
        if request.speech_start_threshold is not None:
            config["speech_start_threshold"] = request.speech_start_threshold
        if request.speech_end_threshold is not None:
            config["speech_end_threshold"] = request.speech_end_threshold
        if request.min_speech_frames is not None:
            config["min_speech_frames"] = request.min_speech_frames
        
        # 3. Save Config to File
        with open(config_path, "w", encoding='utf-8') as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
            
        # 4. Apply Runtime Changes (if AudioManager is active)
        if audio_manager:
            # Device Switch
            if request.device_name:
                audio_manager.set_device_by_name(request.device_name)
            
            # VAD Param Update
            audio_manager.update_params(
                start_threshold=request.speech_start_threshold,
                end_threshold=request.speech_end_threshold,
                min_frames=request.min_speech_frames
            )
            # Note: Voiceprint params usually require restart or deeper reload, 
            # but we can try to update runtime properties if possible.
            # Currently AudioManager takes them in __init__, so restart is safer for those.

        # 5. Log warnings
        if any(x is not None for x in [request.enable_voiceprint_filter, request.voiceprint_threshold, request.voiceprint_profile]):
             logger.warning("⚠️ Voiceprint configuration updated. Verify if restart is needed or if AudioManager handles it.")
            
    except Exception as e:
        logger.error(f"Config Update Failed: {e}", exc_info=True)
        raise HTTPException(500, str(e))
        
    return {"status": "ok", "config": config, "message": "Configuration saved and applied."}

@app.get("/voiceprint/status")
async def get_voiceprint_status():
    """Return current voiceprint configuration and status"""
    global voiceprint_manager
    config_path = app_settings.config_root / "audio_config.json"
    
    try:
        if config_path.exists():
            with open(config_path, encoding='utf-8-sig') as f:
                config = json.load(f)
        else:
            config = {}
        
        # Check if voiceprint profile file exists
        profile = config.get("voiceprint_profile", "default")
        profile_path = Path(f"voiceprint_profiles/{profile}.npy")
        profile_loaded = profile_path.exists()
        
        # Also check if voiceprint_manager has loaded embedding
        if voiceprint_manager and hasattr(voiceprint_manager, 'user_embedding') and voiceprint_manager.user_embedding is not None:
            profile_loaded = True
        
        return {
            "enabled": config.get("enable_voiceprint_filter", False),
            "threshold": config.get("voiceprint_threshold", 0.6),
            "profile": profile,
            "profile_loaded": profile_loaded
        }
    except Exception as e:
        logger.error(f"Failed to get voiceprint status: {e}")
        return {
            "enabled": False,
            "threshold": 0.6,
            "profile": "default",
            "profile_loaded": False
        }

@app.get("/audio/status")
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

@app.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    import uuid
    import asyncio
    connection_id = str(uuid.uuid4())
    active_websockets[connection_id] = websocket
    logger.info(f"Client connected: {connection_id} (Total: {len(active_websockets)})")
    
    # Auto-Start Audio Manager if first client
    if len(active_websockets) == 1 and audio_manager:
        if not audio_manager.is_running:
            logger.info("[Auto-Start] Starting AudioManager (First Client)")
            audio_manager.start()
            
            # Clear queue to prevent stale messages from previous sessions
            while not message_queue.empty():
                try: 
                    message_queue.get_nowait()
                except queue.Empty: 
                    break
                except Exception: 
                    pass # Only pass if truly irrelevant

    try:
        while True:
            # 1. Check outbound queue
            try:
                # Only send if running (prevent leakage)
                if audio_manager and audio_manager.is_running:
                    message = message_queue.get_nowait()
                    await websocket.send_json(message)
                else:
                    await asyncio.sleep(0.1) 
            except queue.Empty:
                pass
            
            # 2. Check inbound (with small timeout to yield control)
            try:
                data = await asyncio.wait_for(websocket.receive(), timeout=0.05)
                # Handle Ping/Pong
                if data.get("type") == "websocket.receive":
                    msg_text = data.get("text")
                    if msg_text:
                        req = json.loads(msg_text)
                        if req.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
            except asyncio.TimeoutError:
                pass
            except WebSocketDisconnect:
                break
                
    except Exception as e:
        logger.error(f"WS Error: {e}")
    finally:
        if connection_id in active_websockets:
            del active_websockets[connection_id]
        logger.info(f"Client disconnected: {connection_id} (Remaining: {len(active_websockets)})")
        
        # Auto-Stop Audio Manager if no clients
        if len(active_websockets) == 0 and audio_manager and audio_manager.is_running:
            logger.info("[Auto-Stop] Stopping AudioManager (No Clients)")
            audio_manager.stop()

if __name__ == "__main__":
    import uvicorn
    from app_config import config
    # 0.0.0.0 for external access if needed, but 127.0.0.1 is safer for local
    uvicorn.run(app, host=config.network.host, port=config.network.stt_port)
