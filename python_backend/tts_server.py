"""
TTS Server - 流式语音合成服务
支持可插拔的 TTS 引擎（Edge TTS 为默认实现）
"""
import logging
import json
import re
import os
import time
import asyncio
import subprocess
from typing import Optional, AsyncGenerator
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import httpx

# 导入本地模块
try:
    from tts_engine_gptsovits import GPTSoVITSEngine
except ImportError:
    from .tts_engine_gptsovits import GPTSoVITSEngine

# 配置日志
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# 确保 FFmpeg (在 GPT-SoVITS/runtime) 在 PATH 中
def ensure_ffmpeg_path():
    # 假设 runtime 在两级目录下 (从 python_backend 向上)
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    ffmpeg_dir = os.path.join(base_dir, "GPT-SoVITS", "runtime")
    if os.path.exists(ffmpeg_dir):
        path = os.environ.get("PATH", "")
        if ffmpeg_dir not in path:
            logger.info(f"Adding FFmpeg to PATH: {ffmpeg_dir}")
            os.environ["PATH"] = f"{ffmpeg_dir};{path}"
    else:
        logger.warning(f"FFmpeg binary directory not found at: {ffmpeg_dir}")

ensure_ffmpeg_path()

app = FastAPI(title="Lumina TTS Service")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

edge_tts_engine: Optional[any] = None
gpt_sovits_engine: Optional[any] = None
emotion_style_map = {}

class TTSRequest(BaseModel):
    text: str
    voice: str = "zh-CN-XiaoxiaoNeural"
    emotion: Optional[str] = None
    engine: str = "edge-tts"
    rate: str = "+0%"
    pitch: str = "+0Hz"


# 全局 HTTP 客户端 (连接复用)
http_client: Optional[httpx.AsyncClient] = None

@app.on_event("startup")
async def startup_event():
    global edge_tts_engine, gpt_sovits_engine, emotion_style_map, http_client
    
    # 初始化 HTTP 客户端
    http_client = httpx.AsyncClient(timeout=None) # 保持长连接
    logger.info("Shared HTTP client initialized")

    logger.info("Initializing Edge TTS...")
    try:
        import edge_tts
        edge_tts_engine = edge_tts
    except ImportError:
        logger.error("edge-tts not installed")
    
    logger.info("Initializing GPT-SoVITS...")
    try:
        gpt_sovits_engine = GPTSoVITSEngine()
        logger.info(f"GPT-SoVITS wrapper loaded")
    except Exception as e:
        logger.warning(f"Failed to load GPT-SoVITS wrapper: {e}")

    try:
        map_path = os.path.join(os.path.dirname(__file__), "tts_emotion_styles.json")
        if os.path.exists(map_path):
            with open(map_path, "r", encoding="utf-8") as f:
                emotion_style_map = json.load(f)
        else:
            emotion_style_map = {}
    except Exception as e:
        logger.warning(f"Failed to load emotion map: {e}")
        emotion_style_map = {}

@app.on_event("shutdown")
async def shutdown_event():
    global http_client
    if http_client:
        await http_client.aclose()
        logger.info("Shared HTTP client closed")
    # Clean up subprocesses if any (handled by their own logic usually)

# ⚡ 修复: 添加连接池重置端点（用于手动恢复）
@app.get("/health/reset_pool")
async def reset_connection_pool():
    """手动重置 HTTP 连接池（当TTS出现问题时使用）"""
    global http_client
    if http_client:
        await http_client.aclose()
        http_client = httpx.AsyncClient(timeout=None)
        logger.info("[Health] HTTP client pool reset")
        return {"status": "ok", "message": "Connection pool reset"}
    return {"status": "error", "message": "No client to reset"}

def parse_emotion_tags(text: str):
    # 1. Extract first emotion tag for style control
    emotion = None
    # Match standard [emotion] formats
    match = re.search(r"\[([a-zA-Z0-9_-]+)\]", text)
    if match:
        emotion = match.group(1)
        
    # 2. Clean Text for TTS
    # Remove all [tags]
    clean_text = re.sub(r"\[.*?\]", "", text)
    # Remove all (parentheses comments) often used for actions
    clean_text = re.sub(r"\(.*?\)", "", clean_text)
    # Remove markdown bold/italic markers
    clean_text = clean_text.replace("*", "").replace("_", "")
    # Remove excess whitespace
    clean_text = re.sub(r"\s+", " ", clean_text).strip()
    
    return clean_text, emotion



async def transcode_to_aac(pcm_iterator: AsyncGenerator[bytes, None], sample_rate=32000) -> AsyncGenerator[bytes, None]:
    """
    流式转码: PCM (Stream) -> FFmpeg -> AAC (Stream)
    """
    # 启动 FFmpeg 进程
    # 输入: s16le PCM, ar=32000 (GPT-SoVITS v1 default), ac=1
    # 输出: adts AAC
    cmd = [
        "ffmpeg", 
        "-f", "s16le", 
        "-ar", str(sample_rate), 
        "-ac", "1", 
        "-i", "pipe:0", 
        "-c:a", "aac", 
        "-b:a", "128k", 
        "-f", "adts", 
        "pipe:1"
    ]
    
    logger.info(f"[Transcoder] Starting FFmpeg: {' '.join(cmd)}")
    process = subprocess.Popen(
        cmd,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, # 捕获错误日志
        bufsize=0 #Unbuffered
    )

    loop = asyncio.get_event_loop()
    
    # 异步写入任务
    async def writer():
        try:
            async for chunk in pcm_iterator:
                if chunk:
                    # 使用 run_in_executor 避免阻塞事件循环
                    await loop.run_in_executor(None, process.stdin.write, chunk)
                    # flush 确保数据立即送入 ffmpeg
                    await loop.run_in_executor(None, process.stdin.flush) 
        except Exception as e:
            logger.error(f"[Transcoder] Writer error: {e}")
        finally:
            try:
                await loop.run_in_executor(None, process.stdin.close)
            except:
                pass
            logger.debug(f"[Transcoder] Writer task finished")

    # 启动写入线程
    writer_task = asyncio.create_task(writer())
    
    # 读取输出并 yield
    try:
        # 持续读取直到 stderr 提示结束或 stdout 关闭
        while True:
            # 每次读取 4KB (AAC frame size usually smaller, but buffer safe)
            chunk = await loop.run_in_executor(None, process.stdout.read, 4096)
            if not chunk:
                break
            yield chunk
    except Exception as e:
        logger.error(f"[Transcoder] Reader error: {e}")
    finally:
        # ⚡ 修复: 加强进程清理，防止僵尸进程
        try:
            writer_task.cancel()
            await asyncio.wait_for(writer_task, timeout=1.0)
        except (asyncio.CancelledError, asyncio.TimeoutError):
            pass
        
        # 强制清理 FFmpeg 进程
        try:
            if process.stdout: process.stdout.close()
            if process.stderr: process.stderr.close()
            
            # 先尝试正常终止
            process.terminate()
            try:
                await asyncio.wait_for(asyncio.to_thread(process.wait), timeout=2.0)
                logger.info("[Transcoder] FFmpeg terminated gracefully")
            except asyncio.TimeoutError:
                # 超时则强制杀死
                logger.warning("[Transcoder] FFmpeg not responding, force killing...")
                process.kill()
                await asyncio.to_thread(process.wait)
                logger.warning("[Transcoder] FFmpeg force killed")
        except Exception as e:
            logger.error(f"[Transcoder] Cleanup error: {e}")


@app.post("/tts/synthesize")
async def synthesize_speech(request: TTSRequest):
    if not request.text.strip():
        raise HTTPException(status_code=400, detail="Text cannot be empty")
    
    clean_text, detected_emotion = parse_emotion_tags(request.text)
    emotion_tag = detected_emotion or request.emotion
    
    # === GPT-SoVITS ===
    if request.engine == "gpt-sovits":
        if not gpt_sovits_engine:
             raise HTTPException(status_code=500, detail="GPT-SoVITS engine not loaded")
        
        try:
            ref_audio_path, ref_text, ref_lang = gpt_sovits_engine.get_ref_audio(request.voice, emotion_tag)
            # ⚡ Fallback Check: Ensure service is actually online before trying to stream
            if not gpt_sovits_engine.is_available:
                gpt_sovits_engine.check_connection() # Last ditch check
                if not gpt_sovits_engine.is_available:
                     raise Exception("Service is marked offline (is_available=False)")

            text_lang = gpt_sovits_engine.detect_language(clean_text)
            
            if not ref_audio_path:
                 raise Exception("Reference audio lookup failed")

            # ⚡ 关键改动: 请求 RAW (PCM) 格式，避免 Server 端 FFmpeg 低效
            # ⭐ 优化: 添加 text_split_method='cut5' (按标点切分) 加速首字生成
            # ⚡ 优化: 添加模型缓存参数，复用 speaker embedding 减少首字延迟
            params = {
                "text": clean_text,
                "text_lang": text_lang,
                "ref_audio_path": ref_audio_path,
                "prompt_text": ref_text,
                "prompt_lang": ref_lang,
                "media_type": "raw", # 请求 PCM Raw Data
                "streaming_mode": "true",
                "text_split_method": "cut5", # 优化: 标点符号切分
                "batch_size": 1,             # 优化: 强制 batch_size=1
                "parallel_infer": True,      # 优化: 尝试开启并行推理
                # ⚡ 新增: 模型缓存参数（如果 GPT-SoVITS API 支持）
                "use_cache": True,           # 启用 speaker embedding 缓存
                "cache_mode": "full"         # 完整缓存模式
            }
            
            target_url = f"{gpt_sovits_engine.api_url}/tts"

            async def raw_stream_generator():
                # 复用全局 http_client
                client = http_client
                if not client:
                    logger.warning("[TTS] Global HTTP client not available, ensuring fallback??")
                    # Should not facilitate fallback here, startup should guarantee it.
                    # Creating temporary for safety if logic fails but ideally shouldn't happen.
                    async with httpx.AsyncClient() as temp_client:
                         async for chunk in stream_request(temp_client, target_url, params):
                             yield chunk
                    return

                async for chunk in stream_request(client, target_url, params):
                    yield chunk

            async def stream_request(client, url, params):
                start_time = time.time()
                logger.info(f"[TTS] Upstream Request: {url} (RAW) | Split: cut5")
                
                try:
                    # ⚡ 修复: 添加请求超时保护 (60秒超时)
                    timeout_config = httpx.Timeout(60.0, connect=10.0, read=60.0)
                    async with client.stream("GET", url, params=params, timeout=timeout_config) as response:
                        if response.status_code != 200:
                            error_text = await response.aread()
                            logger.error(f"GPT-SoVITS API Error: {response.status_code} {error_text}")
                            return
                        
                        first_byte_time = 0
                        chunk_count = 0
                        
                        async for chunk in response.aiter_bytes(chunk_size=4096):
                            cur_time = time.time()
                            if chunk_count == 0:
                                first_byte_time = cur_time
                                logger.info(f"[TTS-RAW] 🟢 First Byte: {first_byte_time - start_time:.4f}s")
                            yield chunk
                            chunk_count += 1
                        
                        # ⚡ 修复: 确保响应完全消费
                        logger.info(f"[TTS] Stream completed: {chunk_count} chunks")
                            
                except asyncio.TimeoutError:
                    logger.error(f"[TTS] Request timeout after 60s")
                except Exception as e:
                    logger.error(f"[TTS] Upstream connection failed: {e}")
            
            # 使用本地 FFmpeg 转码为 AAC
            # 注意: GPT-SoVITS v2 默认采样率可能是 32000，需确认
            # 如果声音变快或变慢，调整 sample_rate
            aac_stream = transcode_to_aac(raw_stream_generator(), sample_rate=32000)
            
            return StreamingResponse(aac_stream, media_type="audio/aac")
            
        except Exception as e:
            logger.error(f"GPT-SoVITS Error: {e}")
            logger.warning("Falling back to Edge TTS...")

    # === Edge TTS (Fallback) ===
    # ⚠️ 注意：Edge TTS 免费版不支持 <mstts:express-as> 情感样式
    # 以下 emotion_style_map 逻辑仅为接口预留，实际输出为纯文本合成
    # 若需启用情感样式，需替换为 Azure Cognitive Services Speech SDK（付费服务）
    if edge_tts_engine is None:
        raise HTTPException(status_code=500, detail="Edge TTS engine not initialized")
        
    target_voice = request.voice
    if request.engine == "gpt-sovits":
        target_voice = "zh-CN-XiaoxiaoNeural"
        
    edge_style = emotion_style_map.get(emotion_tag.lower()) if emotion_tag else None
    logger.info(f"[TTS] Fallback Edge TTS: '{clean_text[:10]}...'")
    
    try:
        # Use clean_text directly. edge_tts will handle it.
        communicate = edge_tts_engine.Communicate(clean_text, target_voice)
        stream_iterator = communicate.stream().__aiter__()
        
        async def edge_stream_generator():
            try:
                async for chunk in stream_iterator:
                    if chunk["type"] == "audio":
                        yield chunk["data"]
            except Exception as e:
                logger.error(f"[EdgeTTS] Stream error: {e}")

        return StreamingResponse(edge_stream_generator(), media_type="audio/mpeg")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tts/voices")
async def list_voices(engine: str = "edge-tts"):
    if engine == "gpt-sovits":
        if gpt_sovits_engine: return {"voices": gpt_sovits_engine.list_voices()}
        return {"voices": [], "error": "GPT-SoVITS not loaded"}
    if edge_tts_engine:
        try:
            voices = await edge_tts_engine.list_voices()
            zh = [v for v in voices if v["Locale"].startswith("zh-")]
            en = [v for v in voices if v["Locale"].startswith("en-")]
            return {"chinese": [{"name": v["ShortName"], "gender": v["Gender"]} for v in zh], "english": [{"name": v["ShortName"], "gender": v["Gender"]} for v in en]}
        except: return {"error": "Failed to list voices"}
    return {"error": "Engine not ready"}

@app.get("/tts/emotions")
async def list_emotions():
    """列出情感样式映射表（仅供参考，Edge TTS 免费版不支持）"""
    return {
        "engine": "Edge TTS",
        "emotions": emotion_style_map,
        "warning": "Edge TTS 免费版不支持情感样式。若需启用，请使用 Azure Cognitive Services 或 GPT-SoVITS 引擎。",
        "supported_engines": {
            "edge-tts": "不支持情感（仅占位）",
            "gpt-sovits": "通过参考音频支持情感克隆"
        }
    }

@app.get("/health")
async def health_check():
    engines = []
    if edge_tts_engine: engines.append("Edge TTS")
    if gpt_sovits_engine:
        # Re-check status on health call (lazy check) or trust the init flag?
        # Trust flag but maybe trigger re-check if user asks? 
        # For now, just check the flag we set on init.
        if gpt_sovits_engine.is_available:
            engines.append("GPT-SoVITS")
        else:
             # Try one more time just in case it came online late
             gpt_sovits_engine.check_connection()
             if gpt_sovits_engine.is_available:
                 engines.append("GPT-SoVITS")
             
    return {"status": "ok", "active_engines": engines}

if __name__ == "__main__":
    import uvicorn
    from app_config import config
    uvicorn.run(app, host=config.network.host, port=config.network.tts_port, log_level="info")
