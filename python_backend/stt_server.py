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
from logger_setup import setup_logger
from model_manager import model_manager
from app_config import config as app_settings


# Initialize Logger (TeeOutput)
logger = setup_logger("stt_server.log")

import numpy as np
import threading
import json
import queue
from typing import Optional, Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from pydantic import BaseModel
from fastapi.middleware.cors import CORSMiddleware

# Engines
from faster_whisper import WhisperModel
# Lazy import for SenseVoice to avoid hard crash if dependencies missing
try:
    from stt_engine_sensevoice import SenseVoiceEngine
    SENSEVOICE_AVAILABLE = True
except ImportError:
    logger.warning("SenseVoiceEngine import failed. SenseVoice will be unavailable.")
    SENSEVOICE_AVAILABLE = False

try:
    from stt_engine_paraformer import ParaformerEngine
    PARAFORMER_AVAILABLE = True
except ImportError:
    logger.warning("ParaformerEngine import failed. Paraformer will be unavailable.")
    PARAFORMER_AVAILABLE = False

from audio_manager import AudioManager
from voiceprint_manager import VoiceprintManager

app = FastAPI(title="Lumina STT Service")

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

MODEL_SIZES = {
    "tiny": "75MB",
    "base": "150MB",
    "small": "500MB",
    "medium": "1.5GB",
    "large-v3": "3GB",
    "sense-voice": "Sherpa-ONNX (SenseVoiceSmall)",
    "paraformer-zh": "Sherpa-ONNX (Paraformer-Large-ZH)",
    "paraformer-en": "Sherpa-ONNX (Paraformer-EN)"
}

CONFIG_FILE = app_settings.config_root / "stt_config.json"

class STTEngineManager:
    def __init__(self):
        self.current_model_name: str = "base"
        self.engine_type: str = "faster_whisper" # 'faster_whisper' or 'sense_voice'
        self.model = None # Can be WhisperModel or SenseVoiceEngine
        self.lock = threading.Lock()
        self.download_status: Dict[str, str] = {name: "idle" for name in MODEL_SIZES}
        self.loading_status = "idle"
        
        self.load_config()

    def load_config(self):
        # Use centralized config (app_settings.stt)
        self.current_model_name = app_settings.stt.model
        
        # Auto-detect engine type based on name
        if self.current_model_name == "sense-voice":
            self.engine_type = "sense_voice"
        elif self.current_model_name.startswith("paraformer"):
            self.engine_type = self.current_model_name.replace("-", "_")
        else:
            self.engine_type = "faster_whisper"


    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"model": self.current_model_name}, f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def load_model(self, name: str):
        with self.lock:
            self.loading_status = "loading"
            logger.info(f"Switching engine to model: {name}...")
            
            try:
                # Cleanup previous model to free VRAM/RAM
                if self.model:
                    logger.info("Unloading previous model...")
                    del self.model
                    import gc
                    gc.collect()
                    self.model = None

                if name == "sense-voice":
                    if not SENSEVOICE_AVAILABLE:
                        raise ImportError("SenseVoice is not available (missing dependencies).")
                    
                    self.engine_type = "sense_voice"
                    engine = SenseVoiceEngine()
                    engine.initialize() # Handles download internally via model_manager
                    self.model = engine
                    logger.info("SenseVoice Engine loaded successfully.")

                elif name == "paraformer-zh":
                    if not PARAFORMER_AVAILABLE:
                         raise ImportError("Paraformer is not available.")
                    self.engine_type = "paraformer_zh"
                    engine = ParaformerEngine(language="zh")
                    engine.initialize()
                    self.model = engine
                    logger.info("Paraformer-ZH Engine loaded successfully.")

                elif name == "paraformer-en":
                    if not PARAFORMER_AVAILABLE:
                         raise ImportError("Paraformer is not available.")
                    self.engine_type = "paraformer_en"
                    engine = ParaformerEngine(language="en")
                    engine.initialize()
                    self.model = engine
                    logger.info("Paraformer-EN Engine loaded successfully.")
                    
                else:
                    self.engine_type = "faster_whisper"
                    # Use model_manager to handle path/download for Whisper too?
                    # Faster-Whisper has its own download logic, but we can direct it to our models dir
                    
                    model_dir = model_manager.base_dir
                    # Note: faster_whisper's download_model(name, output_dir=...) does the job.
                    # We just need to point it to e:\Work\Code\Lumina\models\
                    
                    from faster_whisper import download_model as fw_download
                    
                    # We want each model in its own subdir? faster_whisper handles this if we give it the root?
                    # Actually faster_whisper download_model returns the path to the specific model folder.
                    # Let's keep existing logic: ../models/{name}
                    
                    target_dir = os.path.join(model_manager.base_dir, name)
                    
                    if not os.path.exists(target_dir) or not os.listdir(target_dir):
                        logger.info(f"Downloading Whisper model '{name}' to {target_dir}...")
                        # Use our robust downloader or fw's? FW's is decent but relies on HF.
                        # For robustness, we could use model_manager hook, but let's stick to FW for now
                        # but hijack the env vars just in case it uses cache.
                        model_manager.setup_model_env(name)
                        try:
                            # We deliberately pass 'output_dir' so it downloads HERE
                            model_path = fw_download(name, output_dir=str(target_dir))
                        finally:
                            model_manager.restore_model_env()
                    else:
                        logger.info(f"Found local Whisper files in {target_dir}")
                        model_path = str(target_dir)

                    logger.info(f"Loading Whisper from {model_path}...")
                    
                    # Try CPU first with comprehensive error handling
                    try:
                        self.model = WhisperModel(model_path, device="cpu", compute_type="int8")
                        logger.info(f"Whisper model '{name}' loaded on device='cpu'")
                    except Exception as cpu_error:
                        logger.error(f"CPU initialization also failed: {cpu_error}")
                        raise cpu_error
                    
                    # Warm-up (Separate Step)
                    # 即使 Warm-up 失败，也不弃让加载失败，只暂时模型对象还在执行
                    try:
                        logger.info("Running warm-up inference to verify backend...")
                        dummy_audio = np.zeros(16000, dtype=np.float32)
                        # 暂时不检查结果，只看能不能跑通
                        self.model.transcribe(dummy_audio, beam_size=1)
                        logger.info("Warm-up successful.")
                    except Exception as warmup_err:
                        logger.warning(f"Warm-up failed (non-fatal): {warmup_err}")
                        # 继续，因为可能是 dummy_audio 的问题，不代表模型不能用
                        # If warm-up fails, try to reinitialize with GPU fallback
                        try:
                            self.model = WhisperModel(model_path, device="auto", compute_type="int8")
                            logger.info(f"Whisper model '{name}' loaded on device='auto'")
                        except Exception as e:
                            logger.warning(f"GPU Init failed ({e}), fallback to CPU...")
                            self.model = WhisperModel(model_path, device="cpu", compute_type="int8")

                self.current_model_name = name
                self.loading_status = "idle"
                self.save_config()
                
            except Exception as e:
                self.loading_status = "error"
                logger.error(f"CRITICAL: Failed to load model {name}. Error: {e}", exc_info=True)
                # Recover to base if failed? No, let user know.

    def switch_model_background(self, name: str):
        self.download_status[name] = "downloading"
        try:
            self.load_model(name)
            self.download_status[name] = "completed"
        except Exception as e:
            self.download_status[name] = "failed"
    
    def get_info(self):
        return {
            "current_model": self.current_model_name,
            "engine_type": self.engine_type,
            "loading_status": self.loading_status,
            "models": [    
                {
                    "name": name,
                    "desc": desc,
                    "download_status": self.download_status.get(name, "idle")
                }
                for name, desc in MODEL_SIZES.items()
            ]
        }

engine_manager = STTEngineManager()

@app.on_event("startup")
async def startup_event():
    global audio_manager, voiceprint_manager
    
    # Load model in background
    threading.Thread(target=engine_manager.load_model, args=(engine_manager.current_model_name,)).start()
    
    # Load Audio Config from centralized config
    enable_voiceprint = app_settings.audio.enable_voiceprint_filter
    voiceprint_threshold = app_settings.audio.voiceprint_threshold
    voiceprint_profile = app_settings.audio.voiceprint_profile

    
    if enable_voiceprint:
        try:
            voiceprint_manager = VoiceprintManager()
            if voiceprint_manager.load_voiceprint(voiceprint_profile):
                logger.info(f"✓ Voiceprint enabled. Profile: {voiceprint_profile}")
            else:
                logger.warning(f"⚠️ Profile '{voiceprint_profile}' not found. Voiceprint disabled.")
                enable_voiceprint = False
        except Exception as e:
            logger.error(f"Voiceprint Init Failed: {e}")
            enable_voiceprint = False
            
    # Define Audio Callbacks
    def on_speech_start():
        logger.info("[AudioManager] Speech started")
        message_queue.put({"type": "vad_status", "status": "listening"})
    
    def on_speech_end(audio_data: np.ndarray):
        logger.info(f"[AudioManager] Speech ended. Length: {len(audio_data)}")
        message_queue.put({"type": "vad_status", "status": "thinking"})
        
        if engine_manager.model is None:
            logger.warning("STT Model not ready.")
            message_queue.put({"type": "vad_status", "status": "idle"})
            return
        
        try:
            # === ENGINE DISPATCH ===
            if engine_manager.engine_type == "sense_voice":
                # SenseVoice Logic - returns (segments, info)
                segments, info = engine_manager.model.transcribe(audio_data)
                
                full_transcript = ""
                for segment in segments:
                    segment_text = segment.text.strip()
                    if segment_text:
                        full_transcript += segment_text
                
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
                segments, info = engine_manager.model.transcribe(
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
    
    # audio_manager.start() # ⚡ Defer start to WebSocket connection
    logger.info("AudioManager initialized (Waiting for WS connection to start)")

# --- API Endpoints ---

@app.get("/models/list")
async def get_models():
    """List available STT models and their status"""
    # Define available models
    models = [
        # SenseVoice
        {"name": "sense-voice", "desc": "多语言/情感识别", "engine": "sense_voice", "is_whisper": False},
        
        # Paraformer
        {"name": "paraformer-zh", "desc": "中文/高并发/会议", "engine": "paraformer_zh", "is_whisper": False},
        {"name": "paraformer-en", "desc": "English Only", "engine": "paraformer_en", "is_whisper": False},

        # Faster-Whisper
        {"name": "tiny", "desc": "Minimal (v3)", "engine": "faster_whisper", "is_whisper": True},
        {"name": "base", "desc": "Balanced (v3)", "engine": "faster_whisper", "is_whisper": True},
        {"name": "small", "desc": "Accurate (v3)", "engine": "faster_whisper", "is_whisper": True},
        {"name": "medium", "desc": "Very Accurate", "engine": "faster_whisper", "is_whisper": True},
        {"name": "large-v3", "desc": "Most Accurate (Slow)", "engine": "faster_whisper", "is_whisper": True},
    ]
    
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

        if engine_manager.loading_status == "loading" and engine_manager.current_model_name == m["name"]:
             m["download_status"] = "downloading"

    return {
        "models": models,
        "current_model": engine_manager.current_model_name,
        "engine_type": engine_manager.engine_type,
        "loading_status": engine_manager.loading_status
    }

class SwitchModelRequest(BaseModel):
    model_name: str

@app.post("/models/switch")
async def switch_model(request: SwitchModelRequest, background_tasks: BackgroundTasks):
    if request.model_name not in MODEL_SIZES:
        raise HTTPException(status_code=400, detail="Invalid model name")
    
    # Check if already loading
    if engine_manager.loading_status == "loading":
         raise HTTPException(status_code=409, detail="A model is already loading")

    # Load in background
    background_tasks.add_task(engine_manager.switch_model_background, request.model_name)
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
    
    # ⚡ Auto-Start Audio Manager if first client
    if len(active_websockets) == 1 and audio_manager:
        if not audio_manager.is_running:
            logger.info("[Auto-Start] Starting AudioManager (First Client)")
            audio_manager.start()
            
            # ⚡ Clear queue to prevent stale messages from previous sessions
            while not message_queue.empty():
                try: message_queue.get_nowait()
                except: pass

    try:
        while True:
            # 1. Check outbound queue
            try:
                # ⚡ Only send if running (prevent leakage)
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
        
        # ⚡ Auto-Stop Audio Manager if no clients
        if len(active_websockets) == 0 and audio_manager and audio_manager.is_running:
            logger.info("[Auto-Stop] Stopping AudioManager (No Clients)")
            audio_manager.stop()

if __name__ == "__main__":
    import uvicorn
    from app_config import config
    # 0.0.0.0 for external access if needed, but 127.0.0.1 is safer for local
    uvicorn.run(app, host=config.network.host, port=config.network.stt_port)
