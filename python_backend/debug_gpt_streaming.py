import httpx
import asyncio
import time
import logging
import os
import sys

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

# Config
GPT_SOVITS_URL = "http://127.0.0.1:9880"
TEST_TEXT = "This is a test sentence to verify if the streaming functionality is working correctly. If it is working, we should see chunks arriving immediately."
TEST_TEXT_ZH = "这是一个测试句子，用于验证流式传输功能是否正常工作。如果工作正常，我们应该能看到数据块立即到达。"

async def test_streaming():
    logger.info(f"Target URL: {GPT_SOVITS_URL}")
    
    # 1. Check if server is up
    try:
        async with httpx.AsyncClient() as client:
            resp = await client.get(f"{GPT_SOVITS_URL}/")
            logger.info(f"Server Root Check: {resp.status_code}")
    except Exception as e:
        logger.error(f"Server check failed: {e}")
        logger.error("Please make sure GPT-SoVITS api.py is running on port 9880")
        return

    # 2. Test TTS Streaming
    # Note: We need to match the parameters used in tts_server.py
    # Ideally we should grab a valid ref_audio from the file system, but simply calling the API
    # with whatever is required.
    
    # Let's try to assume the server has some default logic or we need to find a valid ref.
    # In 'tts_engine_gptsovits.py', it looks for local files.
    # We will try to construct a request similar to what tts_server does.
    
    params = {
        "text": TEST_TEXT_ZH,
        "text_lang": "zh",
        "media_type": "ogg",
        "streaming_mode": "true", # Correct parameter name found in api_v2.py
        "text_split_method": "cut5" # Explicitly set split method
    }
    
    # Try to find a reference audio to make the request valid
    # Re-using logic from tts_engine_gptsovits.py roughly
    assets_root = os.path.join(os.path.dirname(__file__), "..", "assets", "emotion_audio")
    # Simplify: just look for ANY wav file in there
    ref_audio_path = ""
    prompt_text = ""
    prompt_lang = "zh"
    
    found = False
    for root, dirs, files in os.walk(assets_root):
        for f in files:
            if f.endswith(".wav") or f.endswith(".mp3"):
                ref_audio_path = os.path.join(root, f)
                # Try to find text
                txt_path = ref_audio_path.rsplit('.', 1)[0] + ".txt"
                if os.path.exists(txt_path):
                    with open(txt_path, 'r', encoding='utf-8') as tf:
                        prompt_text = tf.read().strip()
                else:
                    prompt_text = "你好"
                found = True
                break
        if found: break
        
    if found:
        params["ref_audio_path"] = ref_audio_path
        params["prompt_text"] = prompt_text
        params["prompt_lang"] = prompt_lang
        logger.info(f"Found reference audio: {ref_audio_path}")
    else:
        logger.warning("No reference audio found, request might fail if server requires it.")

    logger.info("Starting Streaming Test...")
    logger.info(f"Params: {params}")

    start_time = time.time()
    first_byte_time = 0
    chunk_count = 0
    total_bytes = 0
    
    try:
        async with httpx.AsyncClient() as client:
            # We use /tts endpoint as seen in tts_engine_gptsovits.py
            async with client.stream("GET", f"{GPT_SOVITS_URL}/tts", params=params, timeout=120.0) as response:
                if response.status_code != 200:
                    logger.error(f"Failed: {response.status_code}")
                    text = await response.aread()
                    logger.error(f"Response: {text}")
                    return

                logger.info("Request sent, waiting for first byte...")
                
                async for chunk in response.aiter_bytes():
                    current_time = time.time()
                    if chunk_count == 0:
                        first_byte_time = current_time
                        ttfb = first_byte_time - start_time
                        logger.info(f"🔴 FIRST BYTE RECEIVED! TTFB: {ttfb:.4f}s")
                    
                    if chunk:
                        chunk_count += 1
                        total_bytes += len(chunk)
                        # Log every 10 chunks or if significant time passed to avoid spam
                        if chunk_count <= 5 or chunk_count % 50 == 0:
                            elapsed = current_time - start_time
                            logger.info(f"  Chunk #{chunk_count}: {len(chunk)} bytes (Time: {elapsed:.4f}s)")
                
    except Exception as e:
        logger.error(f"Stream Error: {e}")
        
    end_time = time.time()
    total_duration = end_time - start_time
    
    if first_byte_time > 0:
        logger.info("-" * 40)
        logger.info(f"✅ Download Complete")
        logger.info(f"Total Duration: {total_duration:.4f}s")
        logger.info(f"TTFB: {first_byte_time - start_time:.4f}s (Time to Start Playing)")
        logger.info(f"Download Phase: {end_time - first_byte_time:.4f}s")
        logger.info(f"Average Speed: {total_bytes / total_duration / 1024:.2f} KB/s")
        logger.info(f"Total Bytes: {total_bytes}")
        
        # Analyze
        download_phase = end_time - first_byte_time
        if (first_byte_time - start_time) > 2.0 and download_phase < 0.5:
             logger.warning("⚠️  SUSPICIOUS: Long TTFB but very fast download. This looks like NON-STREAMING (Server buffer).")
        elif (first_byte_time - start_time) < 1.0:
             logger.info("🚀 LOOKS GOOD: Short TTFB. Likely true streaming.")
        else:
             logger.info("ℹ️  Analysis: Mixed results.")
    else:
        logger.error("❌ No data received.")

if __name__ == "__main__":
    asyncio.run(test_streaming())
