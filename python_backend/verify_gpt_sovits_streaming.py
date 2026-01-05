
import requests
import time
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_streaming():
    # URL of the GPT-SoVITS API (assuming default port)
    url = "http://127.0.0.1:9880/tts"
    
    # Params matching what we send
    params = {
        "text": "测试流式传输的响应速度。",
        "text_lang": "zh",
        "ref_audio_path": "e:\\Work\\Code\\Lumina\\assets\\emotion_audio\\default_voice\\neutral.wav", # Absolute path
        "prompt_text": "今天天气真不错。",
        "prompt_lang": "zh",
        "media_type": "ogg" # Testing if OGG is accepted
    }

    logger.info(f"Connecting to {url} with params: {params}")
    
    try:
        start_time = time.time()
        # Important: stream=True
        with requests.get(url, params=params, stream=True) as response:
            logger.info(f"Response status: {response.status_code}")
            
            if response.status_code != 200:
                logger.error(f"Error: {response.text}")
                return

            logger.info("Headers: " + str(response.headers))
            
            chunk_count = 0
            first_chunk_time = None
            
            for chunk in response.iter_content(chunk_size=4096):
                if not first_chunk_time:
                    first_chunk_time = time.time()
                    logger.info(f"First chunk received in {first_chunk_time - start_time:.4f}s")
                
                chunk_count += 1
                if chunk_count <= 5:
                    logger.info(f"Chunk {chunk_count}: {len(chunk)} bytes (Type: {type(chunk)})")
                
            total_time = time.time()
            logger.info(f"Stream finished. Total chunks: {chunk_count}. Total time: {total_time - start_time:.4f}s")
            
    except Exception as e:
        logger.error(f"Connection failed: {e}")

if __name__ == "__main__":
    test_streaming()
