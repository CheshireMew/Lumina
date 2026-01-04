"""
FastAPI STT Server
纯粹的 WebSocket 转录服务
前端负责 VAD (Voice Activity Detection) 并发送完整音频片段
"""

# [Windows CUDA Fix] Force Python to look for DLLs in the script directory
# This resolves the "cublas64_12.dll not found" error when using local DLLs
# if os.name == 'nt':
#     try:
#         base_path = os.path.dirname(os.path.abspath(__file__))
#         os.add_dll_directory(base_path)
#         print(f"[Init] Added DLL directory: {base_path}")
#     except Exception as e:
#         print(f"[Init] Failed to add DLL directory: {e}")

import logging
import numpy as np
import threading
import json
from typing import Optional, Dict
from pathlib import Path
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, BackgroundTasks
from pydantic import BaseModel
from faster_whisper import WhisperModel, download_model

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
            try:
                # 显式调用 download_model 以确保它存在，这会使用缓存
                download_model(name) 
                
                # 1. 尝试自动/GPU加载
                try:
                    logger.info(f"Attempting to load Whisper model {name} with device='auto'...")
                    candidate_model = WhisperModel(name, device="auto", compute_type="int8")
                    
                    # 2. 预热测试：执行一次空转录以触发潜在的 DLL 加载错误 (如 cublas64_12.dll 缺失)
                    logger.info("Running warm-up inference to verify backend...")
                    dummy_audio = np.zeros(16000, dtype=np.float32)
                    candidate_model.transcribe(dummy_audio, beam_size=1)
                    
                    self.model = candidate_model
                    logger.info(f"Whisper model {name} loaded and verified on device='auto'")
                    
                except Exception as gpu_error:
                    logger.warning(f"GPU/Auto initialization failed ({gpu_error}), falling back to CPU...")
                    self.model = WhisperModel(name, device="cpu", compute_type="int8")
                    logger.info(f"Whisper model {name} loaded on device='cpu'")

                self.current_model_name = name
                self.loading_status = "idle"
                self.save_config()
                
            except Exception as e:
                self.loading_status = "error"
                logger.error(f"Failed to load model {name}: {e}")
                # Fallback if verify failed completely
                if self.model is None:
                    logger.info("Critical failure: Falling back to base model on CPU...")
                    self.current_model_name = "base"
                    self.model = WhisperModel("base", device="cpu", compute_type="int8")

    def switch_model_background(self, name: str):
        """Background task to switch model"""
        self.download_status[name] = "downloading"
        try:
            logger.info(f"Start downloading model {name}...")
            # 下载
            download_model(name)
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
    """启动时加载 Whisper 模型"""
    # 启动时异步加载，避免阻塞（如果是 medium 可能慢）
    # 但为了服务可用性，先加载配置的模型。如果太慢会阻塞启动。
    # 策略：如果配置是 medium/large，且未缓存，可能会久。
    # 我们在新线程中加载，主线程先启动让 API 可用。
    threading.Thread(target=model_manager.load_model, args=(model_manager.current_model_name,)).start()

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

@app.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    await websocket.accept()
    logger.info("New STT client connected")
    
    try:
        while True:
            # 1. 接收前端发来的完整音频片段 (Int16 PCM)
            audio_bytes = await websocket.receive_bytes()
            
            if len(audio_bytes) < 4000: # 忽略太短的杂音 (< 0.25s)
                continue
                
            # 2. 转换格式: Bytes -> Int16 -> Float32
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32767.0
            
            # 3. Whisper 转录
            if model_manager.model is None:
                # 模型未就绪
                logger.warning("Model not ready yet")
                continue

            try:
                # Whisper 流式转录
                segments, info = model_manager.model.transcribe(
                    audio_float32,
                    beam_size=1,  # 优化：降低束搜索以提升首片段速度
                    best_of=1,    # 优化：只保留最佳候选
                    temperature=0.0,
                    vad_filter=False,
                    condition_on_previous_text=False,
                    initial_prompt="以下是普通话的句子。This is a Mandarin Chinese sentence."
                )
                
                full_transcript = ""
                segment_count = 0
                
                # ✅ 流式模式：逐 segment 推送
                for segment in segments:
                    segment_text = segment.text.strip()
                    if segment_text:
                        full_transcript += segment_text
                        segment_count += 1
                        
                        # 立即发送部分结果
                        await websocket.send_json({
                            "type": "partial",
                            "text": full_transcript,
                            "segment": segment_text,
                            "is_final": False
                        })
                        
                        logger.info(f"[Stream] Segment {segment_count}: {segment_text}")
                
                # 所有 segments 结束，发送最终结果
                if full_transcript:
                    logger.info(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")
                    logger.info(f"Final Transcript ({segment_count} segments): {full_transcript}")
                    
                    await websocket.send_json({
                        "type": "transcription",
                        "text": full_transcript,
                        "language": info.language,
                        "is_final": True
                    })
                    
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                
    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765)
