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
        
        # 鎯呮劅闊抽鏍圭洰褰?
        # 鎯呮劅闊抽鏍圭洰褰?(Use CWD/assets since CWD is project root)
        self.assets_root = os.path.join(os.getcwd(), "assets", "emotion_audio")
        
        # 纭繚鏍圭洰褰曞瓨鍦?
        if not os.path.exists(self.assets_root):
            os.makedirs(self.assets_root, exist_ok=True)
            # 鍒涘缓榛樿 voice 鐩綍
            os.makedirs(os.path.join(self.assets_root, "default_voice"), exist_ok=True)

        # 鎯呮劅 -> 鏂囦欢鍚嶆槧灏?(閫氱敤)
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
        
        # 鈿?浼樺寲: 鍙傝€冮煶棰戝唴瀛樼紦瀛?
        self.ref_audio_cache = {}
        self._preload_reference_audios()


    def _preload_reference_audios(self):
        """鍚姩鏃堕鍔犺浇鎵€鏈夊弬鑰冮煶棰戝埌鍐呭瓨缂撳瓨锛岄伩鍏嶈繍琛屾椂纾佺洏I/O"""
        logger.info("[GPT-SoVITS] Preloading reference audios to memory...")
        count = 0
        
        try:
            if not os.path.exists(self.assets_root):
                logger.warning(f"[GPT-SoVITS] Assets root not found: {self.assets_root}")
                return
            
            # 閬嶅巻鎵€鏈夐煶鑹叉枃浠跺す
            for voice_name in os.listdir(self.assets_root):
                voice_dir = os.path.join(self.assets_root, voice_name)
                if not os.path.isdir(voice_dir):
                    continue
                
                # 閬嶅巻鎵€鏈夋儏鎰熸槧灏?
                for emotion, filename in self.emotion_map.items():
                    audio_path = os.path.join(voice_dir, filename)
                    txt_path = audio_path.replace(".wav", ".txt")
                    
                    if not os.path.exists(audio_path):
                        continue
                    
                    # 璇诲彇鍙傝€冩枃鏈?
                    ref_text = ""
                    if os.path.exists(txt_path):
                        with open(txt_path, 'r', encoding='utf-8') as f:
                            ref_text = f.read().strip()
                    else:
                        # Fallback 鏂囨湰
                        if "neutral" in filename: 
                            ref_text = "浠婂ぉ澶╂皵鐪熶笉閿欍€?
                        elif "happy" in filename: 
                            ref_text = "鍝囷紝杩欑湡鏄お妫掍簡锛?
                        elif "sad" in filename: 
                            ref_text = "鎴戠幇鍦ㄦ劅瑙夋湁鐐归毦杩囥€?
                        elif "angry" in filename: 
                            ref_text = "杩欑湡鐨勮鎴戝緢鐢熸皵锛?
                        else:
                            ref_text = "娴嬭瘯闊抽銆?
                    
                    # 鑷姩妫€娴嬭瑷€
                    ref_lang = self.detect_language(ref_text)
                    
                    # 缂撳瓨: (voice, emotion) -> (audio_path, ref_text, ref_lang)
                    # 娉ㄦ剰: 杩欓噷浠嶇劧缂撳瓨璺緞鑰岄潪瀛楄妭锛屽洜涓篏PT-SoVITS API鎺ュ彈鏂囦欢璺緞
                    cache_key = (voice_name, emotion)
                    self.ref_audio_cache[cache_key] = (audio_path, ref_text, ref_lang)
                    count += 1
            
            logger.info(f"[GPT-SoVITS] 鉁?Preloaded {count} reference audios into cache")
            
        except Exception as e:
            logger.error(f"[GPT-SoVITS] Failed to preload reference audios: {e}")

    def check_connection(self):
        """妫€鏌?GPT-SoVITS 鏈嶅姟鏄惁鍦ㄧ嚎"""
        try:
            # 瀹為檯鍙戦€佽姹傛鏌ユ湇鍔$姸鎬?(1绉掕秴鏃?
            resp = requests.get(f"{self.api_url}/", timeout=1)
            if resp.status_code < 500: # 鍙涓嶆槸500锛屽氨绠楅€?
                 self.is_available = True
                 logger.info(f"[GPT-SoVITS] Service online at {self.api_url}")
            else:
                 self.is_available = False
                 logger.warning(f"[GPT-SoVITS] Service responded with error: {resp.status_code}")
        except Exception as e:
            logger.warning(f"[GPT-SoVITS] Service offline or unreachable: {e}")
            self.is_available = False

    def list_voices(self):
        """鍒楀嚭鍙敤闊宠壊锛堝嵆 emotion_audio 涓嬬殑瀛愭枃浠跺す锛?""
        voices = []
        try:
            if os.path.exists(self.assets_root):
                for name in os.listdir(self.assets_root):
                    full_path = os.path.join(self.assets_root, name)
                    if os.path.isdir(full_path):
                        # 妫€鏌ラ噷闈㈡槸鍚︽湁wav鏂囦欢锛屾垨鑰呯洿鎺ヨ涓烘湁鏁?
                        voices.append({
                            "name": name,
                            "gender": "Unknown", # 鏃犳硶鑷姩鍒ゆ柇
                            "Locale": "zh-CN",   # 榛樿鍋囪涓枃
                            "ShortName": name
                        })
        except Exception as e:
            logger.error(f"Failed to list GPT-SoVITS voices: {e}")
        return voices



    @lru_cache(maxsize=128)
    def detect_language(self, text: str) -> str:
        """澶氳瑷€妫€娴? 鏃ヨ(ja) -> 涓枃(zh) -> 鑻辨枃(en)"""
        # 1. 妫€娴嬫棩鏂囧亣鍚?(骞冲亣鍚?\u3040-\u309f, 鐗囧亣鍚?\u30a0-\u30ff)
        for char in text:
            if "\u3040" <= char <= "\u30ff":
                return "ja"
        
        # 2. 妫€娴嬩腑鏂囧瓧绗?(CJK Unified Ideographs)
        # 娉ㄦ剰锛氭棩璇眽瀛椾篃浼氳惤鍏ユ鑼冨洿锛屾墍浠ュ繀椤诲厛妫€娴嬪亣鍚?
        for char in text:
            if "\u4e00" <= char <= "\u9fff":
                return "zh"
                
        # 3. 榛樿鑻辨枃
        return "en"

    def get_ref_audio(self, voice: str, emotion: str) -> tuple[str, str, str]:
        """
        鏍规嵁闊宠壊鍜屾儏鎰熻幏鍙栧弬鑰冮煶棰戯紙浠庡唴瀛樼紦瀛橈級
        鈿?浼樺寲: 浣跨敤鍚姩鏃堕鍔犺浇鐨勭紦瀛橈紝閬垮厤杩愯鏃剁鐩業/O
        """
        if not voice:
            voice = "default_voice"
        if not emotion:
            emotion = "neutral"
            
        # 鈿?浼樺寲: 浼樺厛浠庣紦瀛樿幏鍙?
        cache_key = (voice, emotion.lower())
        if cache_key in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[cache_key]
            return audio_path, ref_text, ref_lang
        
        # Fallback 1: 灏濊瘯璇ラ煶鑹茬殑 neutral
        fallback_key = (voice, "neutral")
        if fallback_key in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[fallback_key]
            logger.warning(f"[Cache Fallback] {cache_key} not found, using {fallback_key}")
            return audio_path, ref_text, ref_lang
        
        # Fallback 2: 灏濊瘯 default_voice + emotion
        fallback_key2 = ("default_voice", emotion.lower())
        if fallback_key2 in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[fallback_key2]
            logger.warning(f"[Cache Fallback] {cache_key} not found, using {fallback_key2}")
            return audio_path, ref_text, ref_lang
        
        # Fallback 3: default_voice + neutral (鏈€鍚庣殑澶囬€?
        ultimate_fallback = ("default_voice", "neutral")
        if ultimate_fallback in self.ref_audio_cache:
            audio_path, ref_text, ref_lang = self.ref_audio_cache[ultimate_fallback]
            logger.error(f"[Cache Miss] {cache_key} not found, using ultimate fallback")
            return audio_path, ref_text, ref_lang
        
        # 瀹屽叏澶辫触锛堜笉搴旇鍙戠敓锛岄櫎闈?assets 鐩綍涓虹┖锛?
        logger.error(f"[Critical] No reference audio available in cache!")
        return None, "", "zh"

    def synthesize(self, text: str, voice: str = "default_voice", emotion: str = "neutral", text_lang: str = None, media_type: str = "aac") -> bytes:

        """
        璋冪敤 GPT-SoVITS API 杩涜鍚堟垚
        """
        # 鑷姩妫€娴嬭緭鍏ユ枃鏈瑷€ (濡傛灉鏈寚瀹?
        if not text_lang:
            text_lang = self.detect_language(text)
            
        ref_audio_path, ref_text, ref_lang = self.get_ref_audio(voice, emotion)
        
        if not ref_audio_path:
            # 濡傛灉娌℃湁鍙傝€冮煶棰戯紝GPT-SoVITS 鍙兘鏃犳硶宸ヤ綔锛堥櫎闈炴ā鍨嬫敮鎸?zero-shot without ref? 閫氬父闇€瑕?ref锛?
            # 鎴栬€呮垜浠彲浠ヤ娇鐢ㄤ竴涓唴缃殑榛樿 ref?
            # 鏆傛椂鎶涘嚭寮傚父璁╀笂灞傚鐞?fallback
            raise Exception("Reference audio lookup failed")

        params = {
            "text": text,
            "text_lang": text_lang,
            "ref_audio_path": ref_audio_path,
            "prompt_text": ref_text,
            "prompt_lang": ref_lang,
            "media_type": media_type,
            "streaming_mode": "true" # 鈿?Fix: Enable actual streaming
        }

        
        try:
            logger.info(f"GPT-SoVITS Req: Text='{text[:10]}...'({text_lang}), Voice='{voice}', Emotion='{emotion}'")
            
            # 鏋勯€犲畬鏁?API URL (榛樿涓?/tts)
            endpoint = f"{self.api_url}/tts"
            
            # 浣跨敤 GET 璇锋眰 (API v2 鏂囨。绀轰緥鎺ㄨ崘 GET 鐢ㄤ簬绠€鍗曟帹鐞嗭紝涔熷彲浠?POST)
            # stream=True 寮€鍚祦寮忔帴鏀?
            with requests.get(endpoint, params=params, stream=True, timeout=60.0) as response:
                if response.status_code == 200:
                    # 浣跨敤 iter_content 杩涜娴佸紡浼犺緭
                    for chunk in response.iter_content(chunk_size=4096):
                        if chunk:
                            yield chunk
                else:
                    raise Exception(f"API Error: {response.status_code} - {response.text}")
                
        except Exception as e:
            logger.error(f"GPT-SoVITS synthesis failed: {e}")
            raise e
