"""
FastAPI STT Server with Backend VAD
后端负责 VAD (Voice Activity Detection) 和音频捕获
使用 AudioManager (sounddevice + webrtcvad) 实现设备隔离和精确VAD
前端通过 WebSocket 接收 VAD 状态和转录结果
"""

import os

# [Windows CUDA Fix] Force Python to look for DLLs in the script directory
# This resolves the "cublas64_12.dll not found" error when using local DLLs
if os.name == 'nt':
    try:
        base_path = os.path.dirname(os.path.abspath(__file__))
        os.add_dll_directory(base_path)
        print(f"[Init] Added DLL directory: {base_path}")
    except Exception as e:
        print(f"[Init] Failed to add DLL directory: {e}")


import logging
import numpy as np
import threading
import json
from typing import Optional, Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from pydantic import BaseModel
from faster_whisper import WhisperModel, download_model
from audio_manager import AudioManager
from voiceprint_manager import VoiceprintManager  # 新增：声纹识别
import queue

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="Lumina STT Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Audio Manager ---
audio_manager: Optional[AudioManager] = None
active_websockets: Dict[str, WebSocket] = {}  # 存储活跃的WebSocket连接
message_queue = queue.Queue()  # 消息队列，用于从音频线程向WebSocket发送消息

# --- Model Management ---

MODEL_SIZES = {
    "tiny": "75MB",
    "base": "150MB",
    "small": "500MB",
    "medium": "1.5GB",
    "large-v3": "3GB"
}

CONFIG_FILE = Path("stt_config.json")

class ModelManager:
    def __init__(self):
        self.current_model_name: str = "base"
        self.model: Optional[WhisperModel] = None
        self.lock = threading.Lock()
        self.download_status: Dict[str, str] = {name: "idle" for name in MODEL_SIZES} # idle, downloading, completed, failed
        self.loading_status = "idle" # idle, loading
        
        self.load_config()

    def load_config(self):
        if CONFIG_FILE.exists():
            try:
                with open(CONFIG_FILE, "r") as f:
                    config = json.load(f)
                    self.current_model_name = config.get("model", "base")
            except Exception as e:
                logger.error(f"Failed to load config: {e}")

    def save_config(self):
        try:
            with open(CONFIG_FILE, "w") as f:
                json.dump({"model": self.current_model_name}, f)
        except Exception as e:
            logger.error(f"Failed to save config: {e}")

    def is_model_downloaded(self, name: str) -> bool:
        # 简单检查：尝试用 faster_whisper 的 download_model 检查缓存，但这可能会触发网络请求
        # 更稳妥的方式是假设如果加载成功就是下载了。
        # 这里我们用一个变通方法：尝试 dry-run download_model，如果它很快返回路径，说明在缓存里。
        # 实际生产中可能需要检查 huggingface cache 目录。
        # 为简化，我们依赖 status 追踪和 lazy loading。
        # 对于初始状态，我们可以假设 'base' 和 'tiny' 是快速可用的。
        # 实际上 faster_whisper 会自动处理缓存。
        return True # 暂时返回 True，依赖 errors 处理

    def load_model(self, name: str):
        with self.lock:
            self.loading_status = "loading"
            logger.info(f"Loading Whisper model: {name}...")
            
            # Define specific local path: ../models/{name}
            # e.g. e:\Work\Code\Lumina\models\medium
            model_dir = Path(__file__).parent.parent / "models" / name
            
            try:
                # 1. 尝试直接加载指定目录 (强制只看这里)
                if model_dir.exists() and any(model_dir.iterdir()):
                    files = [f.name for f in model_dir.iterdir()]
                    logger.info(f"Found local model files in {model_dir}: {files}")
                    model_path_to_use = str(model_dir)
                else:
                    logger.info(f"Model not found in {model_dir}, downloading to this directory...")
                    # 2. 指定 output_dir 下载
                    try:
                        model_path_to_use = download_model(name, output_dir=str(model_dir))
                        logger.info(f"Download complete. Model saved to: {model_path_to_use}")
                    except Exception as download_err:
                        logger.error(f"Download failed: {download_err}")
                        raise download_err

                # 4. Load Model
                try:
                    logger.info(f"Attempting to load Whisper model from {model_path_to_use} with device='auto'...")
                    # 尝试优先加载到 GPU
                    self.model = WhisperModel(model_path_to_use, device="auto", compute_type="int8")
                    logger.info(f"Whisper model {name} loaded on device='auto'")
                except Exception as gpu_error:
                    logger.warning(f"GPU/Auto initialization failed ({gpu_error}), falling back to CPU...")
                    try:
                        self.model = WhisperModel(model_path_to_use, device="cpu", compute_type="int8")
                        logger.info(f"Whisper model {name} loaded on device='cpu'")
                    except Exception as cpu_error:
                        logger.error(f"CPU initialization also failed: {cpu_error}")
                        raise cpu_error

                # 5. Warm-up (Separate Step)
                # 即使 Warm-up 失败，也不要让整个加载过程崩溃，只要模型对象还在就行
                try:
                    logger.info("Running warm-up inference to verify backend...")
                    dummy_audio = np.zeros(16000, dtype=np.float32)
                    # 暂时不检查结果，只看能不能跑通
                    self.model.transcribe(dummy_audio, beam_size=1)
                    logger.info("Warm-up successful.")
                except Exception as warmup_err:
                    logger.warning(f"Warm-up failed (non-fatal): {warmup_err}")
                    # 继续，因为可能是 dummy audio 的问题，不代表模型不能用

                self.current_model_name = name
                self.loading_status = "idle"
                self.save_config()
                
            except Exception as e:
                self.loading_status = "error"
                logger.error(f"CRITICAL: Failed to load model {name} from {model_dir}. Error: {e}")
                import traceback
                logger.error(traceback.format_exc())
                # Do NOT fallback silently to 'base' from cache. Let the user see the error.

    def switch_model_background(self, name: str):
        """Background task to switch model"""
        self.download_status[name] = "downloading"
        try:
            model_dir = Path(__file__).parent.parent / "models" / name
            
            # Only download if not already present
            if not (model_dir.exists() and any(model_dir.iterdir())):
                logger.info(f"Model {name} not found locally. Start downloading to {model_dir}...")
                download_model(name, output_dir=str(model_dir))
            else:
                logger.info(f"Model {name} already exists locally at {model_dir}. Skipping download.")
                
            self.download_status[name] = "completed"
            
            # 加载
            self.load_model(name)
        except Exception as e:
            logger.error(f"Failed to download/load model {name}: {e}")
            self.download_status[name] = "failed"
            self.loading_status = "error"

    def get_info(self):
        return {
            "current_model": self.current_model_name,
            "loading_status": self.loading_status,
            "models": [    
                {
                    "name": name,
                    "size": size,
                    "download_status": self.download_status.get(name, "idle")
                }
                for name, size in MODEL_SIZES.items()
            ]
        }

model_manager = ModelManager()

@app.on_event("startup")
async def startup_event():
    """启动时加载 Whisper 模型和初始化 AudioManager"""
    global audio_manager
    
    # 加载 Whisper 模型（在新线程中加载，避免阻塞启动）
    threading.Thread(target=model_manager.load_model, args=(model_manager.current_model_name,)).start()
    
    # 读取音频配置
    config_path = Path("audio_config.json")
    config = {}
    if config_path.exists():
        with open(config_path, encoding='utf-8-sig') as f:
            config = json.load(f)
    
    enable_voiceprint = config.get("enable_voiceprint_filter", False)
    voiceprint_threshold = config.get("voiceprint_threshold", 0.6)
    voiceprint_profile = config.get("voiceprint_profile", "default")
    
    # 初始化声纹管理器
    voiceprint_mgr = None
    if enable_voiceprint:
        try:
            voiceprint_mgr = VoiceprintManager()
            if voiceprint_mgr.load_voiceprint(voiceprint_profile):
                logger.info(f"✓ 声纹验证已启用，Profile: {voiceprint_profile}")
            else:
                logger.warning(f"⚠️ 声纹Profile未找到: {voiceprint_profile}，声纹验证将被禁用")
                voiceprint_mgr = None
                enable_voiceprint = False
        except Exception as e:
            logger.error(f"声纹管理器初始化失败: {e}，声纹验证将被禁用")
            voiceprint_mgr = None
            enable_voiceprint = False
    else:
        logger.info("声纹验证未启用")
    
    # 初始化 AudioManager - 使用消息队列进行线程间通信
    def on_speech_start():
        """语音开始回调"""
        logger.info("[AudioManager] Speech started")
        message_queue.put({"type": "vad_status", "status": "listening"})
    
    def on_speech_end(audio_data: np.ndarray):
        """语音结束回调 - 执行STT转录"""
        logger.info(f"[AudioManager] Speech ended, audio length: {len(audio_data)} samples")
        
        # 发送thinking状态
        message_queue.put({"type": "vad_status", "status": "thinking"})
        
        # 调用Whisper进行转录
        if model_manager.model is None:
            logger.warning("Model not ready yet")
            message_queue.put({"type": "vad_status", "status": "idle"})
            return
        
        try:
            segments, info = model_manager.model.transcribe(
                audio_data,
                beam_size=1,
                best_of=1,
                temperature=0.0,
                vad_filter=False,
                condition_on_previous_text=False,
                initial_prompt="以下是普通话的句子。This is a Mandarin Chinese sentence."
            )
            
            full_transcript = ""
            for segment in segments:
                segment_text = segment.text.strip()
                if segment_text:
                    full_transcript += segment_text
                    # 流式发送partial结果
                    message_queue.put({
                        "type": "partial",
                        "text": full_transcript,
                        "segment": segment_text,
                        "is_final": False
                    })
            
            # 发送最终转录结果
            if full_transcript:
                logger.info(f"Final Transcript: {full_transcript}")
                message_queue.put({
                    "type": "transcription",
                    "text": full_transcript,
                    "language": info.language,
                    "is_final": True
                })
            else:
                logger.warning("Empty transcript, VAD might have triggered on noise")
        
        except Exception as e:
            logger.error(f"Transcription error: {e}", exc_info=True)
        
        # 发送idle状态
        message_queue.put({"type": "vad_status", "status": "idle"})
    
    def on_vad_status_change(status: str):
        """VAD状态变化回调"""
        # logger.debug(f"[AudioManager] VAD status: {status}")
        # 将状态推送到队列（如 listening 或 idle）
        message_queue.put({"type": "vad_status", "status": status})
    
    audio_manager = AudioManager(
        on_speech_start=on_speech_start,
        on_speech_end=on_speech_end,
        on_vad_status_change=on_vad_status_change,
        voiceprint_manager=voiceprint_mgr,
        enable_voiceprint=enable_voiceprint,
        voiceprint_threshold=voiceprint_threshold,
        # 动态调整VAD灵敏度: 开启声纹时更灵敏(1), 关闭时更严格(3)
        aggressiveness=1 if enable_voiceprint else 3
    )
    
    # 启动音频捕获
    audio_manager.start()
    logger.info("AudioManager initialized and started")

# --- API Endpoints ---

@app.get("/models/list")
async def list_models():
    return model_manager.get_info()

class SwitchModelRequest(BaseModel):
    model_name: str

@app.post("/models/switch")
async def switch_model(request: SwitchModelRequest, background_tasks: BackgroundTasks):
    if request.model_name not in MODEL_SIZES:
        raise HTTPException(status_code=400, detail="Invalid model name")
    
    if model_manager.loading_status == "loading":
         raise HTTPException(status_code=409, detail="A model is already loading")

    # 在后台处理下载和切换，立即返回
    background_tasks.add_task(model_manager.switch_model_background, request.model_name)
    return {"status": "pending", "message": f"Switching to {request.model_name} in background"}

# --- Audio Device Management API ---

@app.get("/audio/devices")
async def list_audio_devices():
    """获取所有可用的音频输入设备"""
    if audio_manager is None:
        raise HTTPException(status_code=500, detail="AudioManager not initialized")
    
    devices = audio_manager.list_devices()
    current_name = audio_manager.device_name
    
    return {
        "devices": devices,
        "current": current_name
    }

# API Request Models
class AudioConfigRequest(BaseModel):
    device_name: Optional[str] = None
    # 声纹配置参数
    enable_voiceprint_filter: Optional[bool] = None
    voiceprint_threshold: Optional[float] = None
    voiceprint_profile: Optional[str] = None

@app.post("/audio/config")
async def update_audio_config(request: AudioConfigRequest):
    """更新音频配置（设备、声纹验证等）"""
    global audio_manager
    
    config_path = Path("audio_config.json")
    config = {}
    if config_path.exists():
        with open(config_path, encoding='utf-8-sig') as f:
            config = json.load(f)
    
    # 更新配置
    if request.device_name is not None:
        config["device_name"] = request.device_name
    if request.enable_voiceprint_filter is not None:
        config["enable_voiceprint_filter"] = request.enable_voiceprint_filter
    if request.voiceprint_threshold is not None:
        config["voiceprint_threshold"] = request.voiceprint_threshold
    if request.voiceprint_profile is not None:
        config["voiceprint_profile"] = request.voiceprint_profile
    
    # 保存配置
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)
    
    # 如果修改了设备，更新AudioManager
    if request.device_name and audio_manager:
        audio_manager.set_device_by_name(request.device_name)
    
    # 声纹配置需要重启stt_server才能生效
    if request.enable_voiceprint_filter is not None or request.voiceprint_threshold is not None:
        logger.warning("⚠️ 声纹配置已更新，请重启 stt_server.py 使配置生效")
    
    return {"status": "ok", "config": config}

@app.get("/voiceprint/status")
async def get_voiceprint_status():
    """获取声纹配置状态"""
    config_path = Path("audio_config.json")
    config = {}
    if config_path.exists():
        with open(config_path, encoding='utf-8-sig') as f:
            config = json.load(f)
    
    enabled = config.get("enable_voiceprint_filter", False)
    threshold = config.get("voiceprint_threshold", 0.6)
    profile = config.get("voiceprint_profile", "default")
    
    # 检查profile是否存在
    profile_path = Path(f"voiceprint_profiles/{profile}.npy")
    profile_loaded = profile_path.exists()
    
    return {
        "enabled": enabled,
        "threshold": threshold,
        "profile": profile,
        "profile_loaded": profile_loaded
    }

class AudioDeviceRequest(BaseModel):
    device_name: str

@app.post("/audio/config")
async def set_audio_device(request: AudioDeviceRequest):
    """设置音频输入设备"""
    if audio_manager is None:
        raise HTTPException(status_code=500, detail="AudioManager not initialized")
    
    success = audio_manager.set_device_by_name(request.device_name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Device not found: {request.device_name}")
    
    # 重启音频捕获以应用新设备
    audio_manager.stop()
    audio_manager.start()
    
    return {
        "status": "success",
        "device_name": request.device_name
    }

@app.get("/audio/status")
async def get_audio_status():
    """获取音频管理器状态"""
    if audio_manager is None:
        raise HTTPException(status_code=500, detail="AudioManager not initialized")
    
    return audio_manager.get_status()

@app.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    
    # 生成连接ID并注册
    import uuid
    connection_id = str(uuid.uuid4())
    active_websockets[connection_id] = websocket
    logger.info(f"New STT client connected: {connection_id}")
    
    try:
        import asyncio
        while True:
            try:
                # 非阻塞地检查消息队列
                try:
                    message = message_queue.get_nowait()
                    # 广播到所有连接
                    await websocket.send_json(message)
                    logger.debug(f"Sent message to {connection_id}: {message.get('type')}")
                except queue.Empty:
                    pass
                
                # 尝试接收前端消息（用于兼容旧模式或ping/pong）
                try:
                    data = await asyncio.wait_for(websocket.receive(), timeout=0.1)
                    
                    if data.get("type") == "websocket.receive":
                        if "text" in data:
                            msg = json.loads(data["text"])
                            if msg.get("type") == "ping":
                                await websocket.send_json({"type": "pong"})
                        
                        # 如果收到音频bytes（旧的前端VAD模式）- fallback支持
                        elif "bytes" in data:
                            audio_bytes = data["bytes"]
                            if len(audio_bytes) >= 4000:
                                # 处理fallback音频（保留旧逻辑）
                                audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
                                audio_float32 = audio_int16.astype(np.float32) / 32767.0
                                
                                if model_manager.model:
                                    segments, info = model_manager.model.transcribe(
                                        audio_float32,
                                        beam_size=1,
                                        best_of=1,
                                        temperature=0.0,
                                        vad_filter=False,
                                        condition_on_previous_text=False,
                                        initial_prompt="以下是普通话的句子。This is a Mandarin Chinese sentence."
                                    )
                                    
                                    full_transcript = ""
                                    for segment in segments:
                                        segment_text = segment.text.strip()
                                        if segment_text:
                                            full_transcript += segment_text
                                            await websocket.send_json({
                                                "type": "partial",
                                                "text": full_transcript,
                                                "segment": segment_text,
                                                "is_final": False
                                            })
                                    
                                    if full_transcript:
                                        await websocket.send_json({
                                            "type": "transcription",
                                            "text": full_transcript,
                                            "language": info.language,
                                            "is_final": True
                                        })
                
                except asyncio.TimeoutError:
                    # 没有收到消息，继续循环
                    pass
            
            except Exception as e:
                logger.error(f"WebSocket loop error: {e}")
                break
                
    except WebSocketDisconnect:
        logger.info(f"Client disconnected: {connection_id}")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
    finally:
        # 清理连接
        if connection_id in active_websockets:
            del active_websockets[connection_id]
            logger.info(f"Removed connection: {connection_id}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
