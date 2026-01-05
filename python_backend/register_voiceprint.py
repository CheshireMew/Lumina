"""
声纹注册脚本 - 手动录制并注册声纹样本

使用方法:
1. 用 Windows 录音机或其他工具录制3-5秒清晰的语音，保存为 my_voice.wav
2. 将文件放在 python_backend 目录下
3. 运行此脚本: python register_voiceprint.py
"""

import sys
import os
from pathlib import Path

# 添加当前目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent))

from voiceprint_manager import VoiceprintManager
import soundfile as sf
import numpy as np

def main():
    print("=" * 60)
    print("声纹注册工具")
    print("=" * 60)
    
    # 初始化声纹管理器
    print("\n[1/4] 初始化声纹管理器...")
    try:
        vp_mgr = VoiceprintManager()
        print("✓ 声纹管理器初始化成功")
    except Exception as e:
        print(f"✗ 初始化失败: {e}")
        return
    
    # 读取音频文件
    audio_file = input("\n[2/4] 请输入音频文件路径 (默认: my_voice.wav): ").strip() or "my_voice.wav"
    
    if not Path(audio_file).exists():
        print(f"✗ 文件不存在: {audio_file}")
        print("\n提示: 请先用录音设备录制3-5秒的清晰语音！")
        return
    
    try:
        audio, sr = sf.read(audio_file)
        print(f"✓ 音频加载成功: {len(audio)/sr:.2f}秒, 采样率 {sr}Hz")
        
        # 确保是单声道
        if audio.ndim > 1:
            audio = audio[:, 0]
            print(f"  (已转换为单声道)")
    except Exception as e:
        print(f"✗ 音频读取失败: {e}")
        return
    
    # Profile 名称
    profile_name = input("\n[3/4] 请输入 Profile 名称 (默认: default): ").strip() or "default"
    
    # 注册声纹
    print(f"\n[4/4] 注册声纹 Profile: {profile_name}...")
    try:
        embedding = vp_mgr.register_voiceprint(
            audio=audio,
            profile_name=profile_name,
            sample_rate=sr
        )
        
        if embedding is not None:
            print(f"\n{'='*60}")
            print(f"✓ 声纹注册成功！")
            print(f"{'='*60}")
            print(f"\nProfile: {profile_name}")
            print(f"保存路径: voiceprint_profiles/{profile_name}.npy")
            print(f"特征维度: {embedding.shape}")
            print(f"\n下一步:")
            print(f"  1. 打开 Lumina 设置界面")
            print(f"  2. 进入 Voice 选项卡")
            print(f"  3. 启用 'Voiceprint Filter (声纹过滤)'")
            print(f"  4. 确认 Profile 名称为: {profile_name}")
            print(f"  5. 调整阈值 (建议从 0.6 开始)")
            print(f"  6. 重启 stt_server.py")
        else:
            print("✗ 声纹注册失败")
    except Exception as e:
        print(f"✗ 注册过程出错: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()
