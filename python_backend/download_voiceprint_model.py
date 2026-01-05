"""
下载 3D-Speaker CAM++ 声纹识别模型
模型来源: k2-fsa/sherpa-onnx 官方发布
"""

import urllib.request
import os
from pathlib import Path

# 模型下载信息（注意：GitHub releases tag 是 speaker-recongition-models，有拼写错误但这是官方tag）
MODEL_URL = "https://github.com/k2-fsa/sherpa-onnx/releases/download/speaker-recongition-models/3dspeaker_speech_campplus_sv_zh_en_16k-common_advanced.onnx"
MODEL_PATH = "voiceprint_profiles/3dspeaker_campplus.onnx"
MODEL_SIZE_MB = 6

def download_with_progress(url: str, destination: str):
    """
    下载文件并显示进度
    """
    def progress_hook(block_num, block_size, total_size):
        downloaded = block_num * block_size
        if total_size > 0:
            percent = min(100, downloaded * 100 / total_size)
            print(f"\r下载进度: {percent:.1f}% ({downloaded / 1024 / 1024:.1f}MB / {total_size / 1024 / 1024:.1f}MB)", end="")
    
    print(f"正在下载模型: {url}")
    urllib.request.urlretrieve(url, destination, progress_hook)
    print("\n✓ 下载完成")

def main():
    # 创建目录
    os.makedirs("voiceprint_profiles", exist_ok=True)
    
    # 检查是否已存在
    if Path(MODEL_PATH).exists():
        print(f"✓ 模型已存在: {MODEL_PATH}")
        file_size = Path(MODEL_PATH).stat().st_size / 1024 / 1024
        print(f"  文件大小: {file_size:.1f}MB")
        return
    
    # 下载模型
    try:
        download_with_progress(MODEL_URL, MODEL_PATH)
        
        # 验证文件大小
        file_size = Path(MODEL_PATH).stat().st_size / 1024 / 1024
        print(f"✓ 模型已保存到: {MODEL_PATH}")
        print(f"  文件大小: {file_size:.1f}MB")
        
        if abs(file_size - MODEL_SIZE_MB) > 1:
            print(f"⚠️ 警告: 文件大小异常 (预期{MODEL_SIZE_MB}MB)")
    
    except Exception as e:
        print(f"✗ 下载失败: {e}")
        print("\n手动下载方法:")
        print(f"1. 访问: {MODEL_URL}")
        print(f"2. 下载后保存到: {MODEL_PATH}")
        return 1
    
    return 0

if __name__ == "__main__":
    exit(main())
