"""
TTS Server - 流式语音合成服务
支持可插拔的 TTS 引擎（Edge TTS 为默认实现）
"""
import logging
from typing import Optional
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import io

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(title="Lumina TTS Service")

# 添加 CORS 中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 允许所有来源（生产环境应该限制为特定域名）
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# TTS 引擎实例（懒加载）
tts_engine: Optional[any] = None

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"  # 默认音色：小小（温柔女声）

import asyncio

@app.on_event("startup")
async def startup_event():
    """启动时初始化 TTS 引擎"""
    global tts_engine
    logger.info("Initializing TTS engine (Edge TTS)...")
    try:
        import edge_tts
        tts_engine = edge_tts
        logger.info("Edge TTS initialized successfully")
    except ImportError:
        logger.error("edge-tts not installed. Run: pip install edge-tts")
        tts_engine = None

@app.post("/tts/synthesize")
async def synthesize_speech(request: TTSRequest):
    """
    语音合成 API
    接收文本和音色，返回音频 (MP3)
    """
    if tts_engine is None:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    logger.info(f"[TTS] Streaming synthesis: '{request.text[:50]}...'")
    
    max_retries = 3
    for attempt in range(max_retries):
        try:
            communicate = tts_engine.Communicate(request.text, request.voice)
            
            # 1. Start the stream iterator manually
            stream_iterator = communicate.stream().__aiter__()
            
            # 2. Pre-flight: Try to get the first chunk *before* returning the StreamingResponse.
            # This ensures that if the connection fails (timeout), we catch it HERE in the loop.
            first_chunk_data = None
            try:
                # We need to loop until we find the first "audio" chunk or the stream ends
                while True:
                    chunk = await stream_iterator.__anext__()
                    if chunk["type"] == "audio":
                        first_chunk_data = chunk["data"]
                        break
            except StopAsyncIteration:
                logger.warning("[TTS] Stream ended without audio data.")
                # If no audio, treating as success but empty? Or fail? 
                # For safety, if retrying, maybe it was a glitch.
                raise Exception("No audio data received")
                
            logger.info(f"[TTS] Connection established (Chunk 1: {len(first_chunk_data)} bytes)")

            # 3. Create a new generator that yields the pre-fetched chunk, then the rest
            async def audio_stream_generator():
                # Yield the pre-buffered chunk
                if first_chunk_data:
                    yield first_chunk_data
                
                # Yield the rest
                chunk_count = 1
                try:
                    async for chunk in stream_iterator:
                        if chunk["type"] == "audio":
                            chunk_count += 1
                            yield chunk["data"]
                    logger.info(f"[TTS] Stream completed ({chunk_count} chunks)")
                except Exception as e:
                    logger.error(f"[TTS] Stream interruption mid-stream: {e}")
                    # Cannot retry here as headers are sent
            
            return StreamingResponse(
                audio_stream_generator(),
                media_type="audio/mpeg"
            )
            
        except Exception as e:
            logger.warning(f"[TTS] Connection attempt {attempt + 1}/{max_retries} failed: {e}")
            if attempt == max_retries - 1:
                logger.error(f"[TTS] All retries failed: {e}")
                raise HTTPException(status_code=500, detail=f"TTS Service Unavailable: {str(e)}")
            
            # Exponential backoff? Or simple sleep
            await asyncio.sleep(1.5)


@app.get("/tts/voices")
async def list_voices():
    """列出所有可用音色"""
    if tts_engine is None:
        raise HTTPException(status_code=500, detail="TTS engine not initialized")
    
    try:
        voices = await tts_engine.list_voices()
        # 筛选中文和英文音色 (移除切片限制，返回所有可用音色)
        zh_voices = [v for v in voices if v["Locale"].startswith("zh-")]
        en_voices = [v for v in voices if v["Locale"].startswith("en-")]
        
        return {
            "chinese": [{"name": v["ShortName"], "gender": v["Gender"]} for v in zh_voices],
            "english": [{"name": v["ShortName"], "gender": v["Gender"]} for v in en_voices]
        }
    except Exception as e:
        logger.error(f"Failed to list voices: {e}")
        return {"error": str(e)}

@app.get("/health")
async def health_check():
    return {"status": "ok", "engine": "Edge TTS" if tts_engine else "Not initialized"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="info")
