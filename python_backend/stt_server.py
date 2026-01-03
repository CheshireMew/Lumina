"""
FastAPI STT Server
纯粹的 WebSocket 转录服务
前端负责 VAD (Voice Activity Detection) 并发送完整音频片段
"""
import logging
import numpy as np
from typing import Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from faster_whisper import WhisperModel

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lumina STT Service")

# 全局 Whisper 模型
whisper_model: Optional[WhisperModel] = None

@app.on_event("startup")
async def startup_event():
    """启动时加载 Whisper 模型"""
    global whisper_model
    logger.info("Loading Whisper model...")
    # 使用 faster-whisper，默认 base 模型，CPU int8
    whisper_model = WhisperModel("base", device="cpu", compute_type="int8")
    logger.info("Whisper model loaded successfully")

@app.websocket("/ws/stt")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket STT 端点
    接收 Int16 PCM 音频数据 (完整的一句话)，返回转录文本
    """
    await websocket.accept()
    logger.info("Client connected")
    
    try:
        while True:
            # 1. 接收前端发来的完整音频片段 (Int16 PCM)
            audio_bytes = await websocket.receive_bytes()
            
            if len(audio_bytes) < 2000: # 忽略太短的杂音 (< 0.1s)
                continue
                
            logger.info(f"Received audio segment: {len(audio_bytes)} bytes")
            
            # 2. 转换格式: Bytes -> Int16 -> Float32
            # VAD-React 发送的是 16kHz mono 16-bit PCM
            audio_int16 = np.frombuffer(audio_bytes, dtype=np.int16)
            audio_float32 = audio_int16.astype(np.float32) / 32767.0
            
            # 3. Whisper 转录
            try:
                segments, info = whisper_model.transcribe(
                    audio_float32,
                    # language="zh", # 移除强制中文，允许自动检测
                    beam_size=5,
                    vad_filter=False, 
                    # 提示模型：可以是中文或英文，且中文倾向于简体
                    initial_prompt="Hello, 你好。请用简体中文 (Simplified Chinese) 或 English 转录。"
                )
                
                transcript = "".join([seg.text for seg in segments]).strip()
                
                if transcript:
                    logger.info(f"Detected language: {info.language} (prob: {info.language_probability:.2f})")
                    logger.info(f"Transcript: {transcript}")
                    await websocket.send_json({
                        "type": "transcript",
                        "text": transcript
                    })
                # else:
                #     logger.info("Empty transcript")
                    
            except Exception as e:
                logger.error(f"Transcription error: {e}")
                await websocket.send_json({
                    "type": "error",
                    "message": f"Transcription failed: {str(e)}"
                })

    except WebSocketDisconnect:
        logger.info("Client disconnected")
    except Exception as e:
        logger.error(f"WebSocket error: {e}")

@app.get("/health")
async def health_check():
    return {"status": "ok", "ready": whisper_model is not None}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8765, log_level="info")
