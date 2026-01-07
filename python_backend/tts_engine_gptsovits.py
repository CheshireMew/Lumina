import os
import requests
import logging
import json
from typing import Optional
from functools import lru_cache

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
        
        # ⚡ 优化: 参考音频内存缓存
        self.ref_audio_cache = {}
        self._preload_reference_audios()


    def _preload_reference_audios(self):
        """启动时预加载所有参考音频到内存缓存，避免运行时磁盘I/O"""
        logger.info("[GPT-SoVITS] Preloading reference audios to memory...")
        count = 0
        
        try:
            if not os.path.exists(self.assets_root):
                logger.warning(f"[GPT-SoVITS] Assets root not found: {self.assets_root}")
                return
            
            # 遍历所有音色文件夹
            for voice_name in os.listdir(self.assets_root):
                voice_dir = os.path.join(self.assets_root, voice_name)
                if not os.path.isdir(voice_dir):
                    continue
                
                # 遍历所有情感映射
                for emotion, filename in self.emotion_map.items():
                    audio_path = os.path.join(voice_dir, filename)
                    txt_path = audio_path.replace(".wav", ".txt")
                    
                    if not os.path.exists(audio_path):
                        continue
                    
                    # 读取参考文本
                    ref_text = ""
                    if os.path.exists(txt_path):
                        with open(txt_path, 'r', encoding='utf-8') as f:
                            ref_text = f.read().strip()
                    else:
                        # Fallback 文本
                        if "neutral" in filename: 
                            ref_text = "今天天气真不错。"
                        elif "happy" in filename: 
                            ref_text = "哇，这真是太棒了！"
                        elif "sad" in filename: 
                            ref_text = "我现在感觉有点难过。"
                        elif "angry" in filename: 
                            ref_text = "这真的让我很生气！"
                        else:
                            ref_text = "测试音频。"
                    
                    # 自动检测语言
                    ref_lang = self.detect_language(ref_text)
                    
                    # 缓存: (voice, emotion) -> (audio_path, ref_text, ref_lang)
                    # 注意: 这里仍然缓存路径而非字节，因为GPT-SoVITS API接受文件路径
                    cache_key = (voice_name, emotion)
                    self.ref_audio_cache[cache_key] = (audio_path, ref_text, ref_lang)
                    count += 1
            
            logger.info(f"[GPT-SoVITS] ✅ Preloaded {count} reference audios into cache")
            
        except Exception as e:
            logger.error(f"[GPT-SoVITS] Failed to preload reference audios: {e}")

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



    @lru_cache(maxsize=128)
    def detect_language(self, text: str) -> str:
        """多语言检测: 日语(ja) -> 中文(zh) -> 英文(en)"""
        # 1. 检测日文假名 (平假名 \u3040-\u309f, 片假名 \u30a0-\u30ff)
        for char in text:
            if "\u3040" <= char <= "\u30ff":
                return "ja"
        
        # 2. 检测中文字符 (CJK Unified Ideographs)
        # 注意：日语汉字也会落入此范围，所以必须先检测假名
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                return "zh"
                
        # 3. 默认英文
        return "en"

    def get_ref_audio(self, voice: str, emotion: str) -> tuple[str, str, str]:
        """
        根据音色和情感获取参考音频（从内存缓存）
        ⚡ 优化: 使用启动时预加载的缓存，避免运行时磁盘I/O
        """
        if not voice:
            voice = "default_voice"
        if not emotion:
            emotion = "neutral"
            
        # ⚡ 优化: 优先从缓存获取
        cache_key = (voice, emotion.lower())
        if cache_key in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[cache_key]
            return audio_path, ref_text, ref_lang
        
        # Fallback 1: 尝试该音色的 neutral
        fallback_key = (voice, "neutral")
        if fallback_key in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[fallback_key]
            logger.warning(f"[Cache Fallback] {cache_key} not found, using {fallback_key}")
            return audio_path, ref_text, ref_lang
        
        # Fallback 2: 尝试 default_voice + emotion
        fallback_key2 = ("default_voice", emotion.lower())
        if fallback_key2 in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[fallback_key2]
            logger.warning(f"[Cache Fallback] {cache_key} not found, using {fallback_key2}")
            return audio_path, ref_text, ref_lang
        
        # Fallback 3: default_voice + neutral (最后的备选)
        ultimate_fallback = ("default_voice", "neutral")
        if ultimate_fallback in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[ultimate_fallback]
            logger.error(f"[Cache Miss] {cache_key} not found, using ultimate fallback")
            return audio_path, ref_text, ref_lang
        
        # 完全失败（不应该发生，除非 assets 目录为空）
        logger.error(f"[Critical] No reference audio available in cache!")
        return None, "", "zh"

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
