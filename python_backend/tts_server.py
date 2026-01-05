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

def parse_emotion_tags(text: str):
    match = re.search(r"^\[([a-zA-Z]+)\]", text.strip())
    if match:
        emotion = match.group(1)
        clean_text = re.sub(r"^\[([a-zA-Z]+)\]", "", text.strip()).strip()
        return clean_text, emotion
    return text, None

def wrap_with_ssml(text: str, voice: str, style: str = None):
    """
    生成 SSML (Speech Synthesis Markup Language)
    
    注意：style 参数仅适用于 Azure Cognitive Services
    Edge TTS 免费版会忽略 <mstts:express-as> 标签
    """
    safe_text = text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
    if style:  # 此分支在 Edge TTS 下无效，保留仅为兼容性
        return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='en-US'>
    <voice name='{voice}'>
        <mstts:express-as style='{style}'>
            {safe_text}
        </mstts:express-as>
    </voice>
</speak>"""
    return f"""<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xml:lang='en-US'>
    <voice name='{voice}'>
        {safe_text}
    </voice>
</speak>"""

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
                    # flush 确保数据立即送入 ffmpeg (影响不大但以防万一)
                    await loop.run_in_executor(None, process.stdin.flush) 
        except Exception as e:
            logger.error(f"[Transcoder] Writer error: {e}")
        finally:
            try:
                await loop.run_in_executor(None, process.stdin.close)
            except:
                pass

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
        # 清理
        writer_task.cancel()
        if process.stdout: process.stdout.close()
        if process.stderr: process.stderr.close()
        process.terminate()
        logger.info("[Transcoder] FFmpeg terminated")


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
            text_lang = gpt_sovits_engine.detect_language(clean_text)
            
            if not ref_audio_path:
                 raise Exception("Reference audio lookup failed")

            # ⚡ 关键改动: 请求 RAW (PCM) 格式，避免 Server 端 FFmpeg 低效
            # ⭐ 优化: 添加 text_split_method='cut5' (按标点切分) 加速首字生成
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
                "parallel_infer": True       # 优化: 尝试开启并行推理
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
                    # 使用 client.stream 保持连接复用
                    async with client.stream("GET", url, params=params, timeout=60.0) as response:
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
    ssml_text = wrap_with_ssml(clean_text, target_voice, edge_style)  # style 参数当前无效
    logger.info(f"[TTS] Fallback Edge TTS: '{clean_text[:10]}...'")
    
    try:
        communicate = edge_tts_engine.Communicate(ssml_text, target_voice)
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
    if gpt_sovits_engine: engines.append("GPT-SoVITS")
    return {"status": "ok", "active_engines": engines}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="127.0.0.1", port=8766, log_level="info")
