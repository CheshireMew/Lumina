"""
澹扮汗娉ㄥ唽鑴氭湰 - 鎵嬪姩褰曞埗骞舵敞鍐屽0绾规牱鏈?

浣跨敤鏂规硶:
1. 鐢?Windows 褰曢煶鏈烘垨鍏朵粬宸ュ叿褰曞埗3-5绉掓竻鏅扮殑璇煶锛屼繚瀛樹负 my_voice.wav
2. 灏嗘枃浠舵斁鍦?python_backend 鐩綍涓?
3. 杩愯姝よ剼鏈? python register_voiceprint.py
"""

import sys
import os
from pathlib import Path

# 娣诲姞 python_backend 鏍圭洰褰曞埌 Python 璺緞 (3绾у悜涓?
sys.path.insert(0, str(Path(__file__).parents[3]))

# Absolute import works if python_backend/ is in sys.path
from .manager import VoiceprintManager
import soundfile as sf
import numpy as np

def main():
    print("=" * 60)
    print("澹扮汗娉ㄥ唽宸ュ叿")
    print("=" * 60)
    
    # 鍒濆鍖栧0绾圭鐞嗗櫒
    print("\n[1/4] 鍒濆鍖栧0绾圭鐞嗗櫒...")
    try:
        vp_mgr = VoiceprintManager()
        print("鉁?澹扮汗绠$悊鍣ㄥ垵濮嬪寲鎴愬姛")
    except Exception as e:
        print(f"鉁?鍒濆鍖栧け璐? {e}")
        return
    
    # 璇诲彇闊抽鏂囦欢
    audio_file = input("\n[2/4] 璇疯緭鍏ラ煶棰戞枃浠惰矾寰?(榛樿: my_voice.wav): ").strip() or "my_voice.wav"
    
    if not Path(audio_file).exists():
        print(f"鉁?鏂囦欢涓嶅瓨鍦? {audio_file}")
        print("\n鎻愮ず: 璇峰厛鐢ㄥ綍闊宠澶囧綍鍒?-5绉掔殑娓呮櫚璇煶锛?)
        return
    
    try:
        audio, sr = sf.read(audio_file)
        print(f"鉁?闊抽鍔犺浇鎴愬姛: {len(audio)/sr:.2f}绉? 閲囨牱鐜?{sr}Hz")
        
        # 纭繚鏄崟澹伴亾
        if audio.ndim > 1:
            audio = audio[:, 0]
            print(f"  (宸茶浆鎹负鍗曞0閬?")
    except Exception as e:
        print(f"鉁?闊抽璇诲彇澶辫触: {e}")
        return
    
    # Profile 鍚嶇О
    profile_name = input("\n[3/4] 璇疯緭鍏?Profile 鍚嶇О (榛樿: default): ").strip() or "default"
    
    # 娉ㄥ唽澹扮汗
    print(f"\n[4/4] 娉ㄥ唽澹扮汗 Profile: {profile_name}...")
    try:
        success = vp_mgr.register_voiceprint(
            audio=audio,
            profile_name=profile_name,
            sample_rate=sr
        )
        
        if success:
            print(f"\n{'='*60}")
            print(f"鉁?澹扮汗娉ㄥ唽鎴愬姛锛?)
            print(f"{'='*60}")
            print(f"\nProfile: {profile_name}")
            print(f"淇濆瓨璺緞: voiceprint_profiles/{profile_name}.npy")
            # print(f"鐗瑰緛缁村害: {embedding.shape}") # Removed as API returns bool
            print(f"\n涓嬩竴姝?")
            print(f"  1. 鎵撳紑 Lumina 璁剧疆鐣岄潰")
            print(f"  2. 杩涘叆 Voice 閫夐」鍗?)
            print(f"  3. 鍚敤 'Voiceprint Filter (澹扮汗杩囨护)'")
            print(f"  4. 纭 Profile 鍚嶇О涓? {profile_name}")
            print(f"  5. 璋冩暣闃堝€?(寤鸿浠?0.6 寮€濮?")
            print(f"  6. 閲嶅惎 stt_server.py")
        else:
            print("鉁?澹扮汗娉ㄥ唽澶辫触")
    except Exception as e:
        print(f"鉁?娉ㄥ唽杩囩▼鍑洪敊: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
