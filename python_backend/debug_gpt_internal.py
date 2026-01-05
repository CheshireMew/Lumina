
import logging
import sys
from tts_engine_gptsovits import GPTSoVITSEngine

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_internal_engine():
    logger.info("Initializing Engine...")
    engine = GPTSoVITSEngine()
    
    text = "测试内部类生成器。"
    logger.info(f"Synthesizing: {text}")
    
    try:
        # Use the same parameters as the server
        gen = engine.synthesize(text, voice="zh-CN-XiaoyiNeural", emotion="neutral")
        
        logger.info(f"Result type: {type(gen)}")
        
        count = 0
        for chunk in gen:
            count += 1
            if count == 1:
                logger.info(f"First chunk type: {type(chunk)}")
                logger.info(f"First chunk len: {len(chunk)}")
            
            if not isinstance(chunk, bytes):
                logger.error(f"CRITICAL: Chunk is {type(chunk)}, expected bytes!")
                break
                
        logger.info(f"Total chunks: {count}")
        
    except Exception as e:
        logger.error(f"Error: {e}")

if __name__ == "__main__":
    test_internal_engine()
