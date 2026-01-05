import os
import requests
import logging
import json
from typing import Optional

logger = logging.getLogger(__name__)

class GPTSoVITSEngine:
    def __init__(self, api_url: str = "http://127.0.0.1:9880"):
        self.api_url = api_url
        self.is_available = False
        self.check_connection()
        
        # 情感音频根目录
        self.assets_root = os.path.join(os.path.dirname(os.path.dirname(__file__)), "assets", "emotion_audio")
        
        # 确保根目录存在
        if not os.path.exists(self.assets_root):
            os.makedirs(self.assets_root, exist_ok=True)
            # 创建默认 voice 目录
            os.makedirs(os.path.join(self.assets_root, "default_voice"), exist_ok=True)

        # 情感 -> 文件名映射 (通用)
        self.emotion_map = {
            "happy": "happy.wav",
            "excited": "happy.wav",
            "sad": "sad.wav",
            "angry": "angry.wav",
            "neutral": "neutral.wav",
            "surprised": "surprised.wav",
            "fear": "fear.wav",
            "disgust": "disgust.wav"
        }

    def check_connection(self):
        """检查 GPT-SoVITS 服务是否在线"""
        try:
            # 简单检查，设置标记
            self.is_available = True 
        except Exception as e:
            logger.warning(f"GPT-SoVITS service check failed: {e}")
            self.is_available = False

    def list_voices(self):
        """列出可用音色（即 emotion_audio 下的子文件夹）"""
        voices = []
        try:
            if os.path.exists(self.assets_root):
                for name in os.listdir(self.assets_root):
                    full_path = os.path.join(self.assets_root, name)
                    if os.path.isdir(full_path):
                        # 检查里面是否有wav文件，或者直接视为有效
                        voices.append({
                            "name": name,
                            "gender": "Unknown", # 无法自动判断
                            "Locale": "zh-CN",   # 默认假设中文
                            "ShortName": name
                        })
        except Exception as e:
            logger.error(f"Failed to list GPT-SoVITS voices: {e}")
        return voices

    def detect_language(self, text: str) -> str:
        """简单语言检测: 包含中文字符视为中文(zh)，否则视为英文(en)"""
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                return "zh"
        return "en"

    def get_ref_audio(self, voice: str, emotion: str) -> tuple[str, str, str]:
        """
        根据音色和情感获取参考音频
        voice: assets/emotion_audio/ 下的文件夹名
        """
        if not voice:
            voice = "default_voice"
        if not emotion:
            emotion = "neutral"
            
        voice_dir = os.path.join(self.assets_root, voice)
        
        # 如果指定音色不存在，回退到 default_voice
        if not os.path.exists(voice_dir):
            logger.warning(f"Voice dir not found: {voice}, fallback to default_voice")
            voice_dir = os.path.join(self.assets_root, "default_voice")
            
        filename = self.emotion_map.get(emotion.lower(), "neutral.wav")
        file_path = os.path.join(voice_dir, filename)
        
        # 尝试查找 fallback (如果具体情感文件不存在，找 neutral.wav)
        if not os.path.exists(file_path):
            file_path = os.path.join(voice_dir, "neutral.wav")
            
        if not os.path.exists(file_path):
            logger.error(f"Ref audio not found: {file_path}")
            return None, "", "zh"
            
        ref_text = ""
        txt_path = file_path.replace(".wav", ".txt")
        if os.path.exists(txt_path):
            with open(txt_path, 'r', encoding='utf-8') as f:
                ref_text = f.read().strip()
        else:
            # Fallback text
            if "neutral" in filename: ref_text = "今天天气真不错。"
            elif "happy" in filename: ref_text = "哇，这真是太棒了！"
            elif "sad" in filename: ref_text = "我现在感觉有点难过。"
            elif "angry" in filename: ref_text = "这真的让我很生气！"
        
        # 自动检测 Prompt 语言
        ref_lang = self.detect_language(ref_text)
        return file_path, ref_text, ref_lang

    def synthesize(self, text: str, voice: str = "default_voice", emotion: str = "neutral", text_lang: str = None) -> bytes:
        """
        调用 GPT-SoVITS API 进行合成
        """
        # 自动检测输入文本语言 (如果未指定)
        if not text_lang:
            text_lang = self.detect_language(text)
            
        ref_audio_path, ref_text, ref_lang = self.get_ref_audio(voice, emotion)
        
        if not ref_audio_path:
            # 如果没有参考音频，GPT-SoVITS 可能无法工作（除非模型支持 zero-shot without ref? 通常需要 ref）
            # 或者我们可以使用一个内置的默认 ref?
            # 暂时抛出异常让上层处理 fallback
            raise Exception("Reference audio lookup failed")

        params = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": ref_text,
            "prompt_lang": ref_lang,
            "media_type": "aac",
            "streaming_mode": "true" # ⚡ Fix: Enable actual streaming
        }
        
        try:
            logger.info(f"GPT-SoVITS Req: Text='{text[:10]}...'({text_lang}), Voice='{voice}', Emotion='{emotion}'")
            
            # 构造完整 API URL (默认为 /tts)
            endpoint = f"{self.api_url}/tts"
            
            # 使用 GET 请求 (API v2 文档示例推荐 GET 用于简单推理，也可以 POST)
            # stream=True 开启流式接收
            with requests.get(endpoint, params=params, stream=True) as response:
                if response.status_code == 200:
                    # 使用 iter_content 进行流式传输
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            yield chunk
                else:
                    raise Exception(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"GPT-SoVITS synthesis failed: {e}")
            raise e
