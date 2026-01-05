
import asyncio
import httpx
import logging
import os

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Mocking the engine logic for path retrieval
ASSETS_ROOT = "e:\\Work\\Code\\Lumina\\assets\\emotion_audio"
REF_AUDIO = os.path.join(ASSETS_ROOT, "default_voice", "neutral.wav")

async def test_stream():
    url = "http://127.0.0.1:9880/tts"
    params = {
        "text": "测试 HTTPX 异步流式传输是否稳定。",
        "text_lang": "zh",
        "ref_audio_path": REF_AUDIO,
        "prompt_text": "今天天气真不错。",
        "prompt_lang": "zh",
        "media_type": "ogg"
    }

    logger.info(f"Starting request to {url}")
    
    async with httpx.AsyncClient() as client:
        try:
            async with client.stream("GET", url, params=params, timeout=60.0) as response:
                logger.info(f"Status: {response.status_code}")
                if response.status_code != 200:
                    text = await response.aread()
                    logger.error(f"Error body: {text}")
                    return

                count = 0
                async for chunk in response.aiter_bytes(chunk_size=4096):
                    count += 1
                    if count == 1:
                        logger.info(f"First chunk: {len(chunk)} bytes")
                    # print(".", end="", flush=True)
                
                logger.info(f"\nStream finished. Total chunks: {count}")
        except Exception as e:
            logger.error(f"Stream failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_stream())
