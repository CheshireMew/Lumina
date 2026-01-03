from fish_audio_sdk import Session, TTSRequest
from typing import Optional
import time

class TTSService:
    def __init__(self, api_key: str, reference_id: str):
        self.api_key = api_key
        self.reference_id = reference_id
        self.session = Session(api_key)
    
    def generate_audio(self, text: str) -> bytes:
        max_retries = 3
        retry_delay = 1  # 初始延迟1秒
        
        for attempt in range(max_retries):
            try:
                audio_data = b"".join(self.session.tts(TTSRequest(
                    reference_id=self.reference_id,
                    text=text
                )))
                return audio_data
            except Exception as e:
                if attempt < max_retries - 1:  # 如果不是最后一次尝试
                    print(f"TTS Error on attempt {attempt + 1}: {str(e)}")
                    time.sleep(retry_delay)
                    retry_delay *= 2  # 指数退避，每次失败后等待时间翻倍
                else:
                    print(f"TTS Error: All {max_retries} attempts failed. Last error: {str(e)}")
                    return b""  # 所有重试都失败后返回空音频数据 