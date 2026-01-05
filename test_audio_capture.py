"""
临时音频调试脚本 - 测试AudioManager捕获的音频
"""

import sounddevice as sd
import webrtcvad
import numpy as np
from collections import deque
import wave

# 配置
SAMPLE_RATE = 16000
DURATION = 5  # 录制5秒
FRAME_DURATION_MS = 30
FRAME_SIZE = int(SAMPLE_RATE * FRAME_DURATION_MS / 1000)

print("=== 音频捕获测试 ===")
print(f"采样率: {SAMPLE_RATE} Hz")
print(f"帧大小: {FRAME_SIZE} samples ({FRAME_DURATION_MS}ms)")
print("\n可用设备:")

devices = sd.query_devices()
input_devices = []
for i, dev in enumerate(devices):
    if dev['max_input_channels'] > 0:
        print(f"  [{i}] {dev['name']} ({dev['max_input_channels']} ch)")
        input_devices.append(i)

device_index = int(input("\n选择设备索引: "))

print(f"\n开始录制 {DURATION} 秒...")
audio_frames = []

def audio_callback(indata, frames, time, status):
    if status:
        print(f"⚠️  {status}")
    audio_frame = indata[:, 0] if indata.ndim > 1 else indata
    audio_frames.append(audio_frame.copy())

with sd.InputStream(
    device=device_index,
    samplerate=SAMPLE_RATE,
    channels=1,
    dtype='float32',
    blocksize=FRAME_SIZE,
    callback=audio_callback
):
    sd.sleep(DURATION * 1000)

print(f"录制完成！共 {len(audio_frames)} 帧")

# 合并音频
audio_data = np.concatenate(audio_frames)
print(f"\n📊 音频数据统计:")
print(f"  总样本数: {len(audio_data)}")
print(f"  数据类型: {audio_data.dtype}")
print(f"  数值范围: [{audio_data.min():.4f}, {audio_data.max():.4f}]")
print(f"  均值: {audio_data.mean():.4f}")
print(f"  标准差: {audio_data.std():.4f}")

# 检查是否有有效信号
if abs(audio_data.max()) < 0.001 and abs(audio_data.min()) < 0.001:
    print("\n❌ 警告：音频信号太弱！可能麦克风未工作或被静音")
else:
    print("\n✅ 音频信号正常")

# 保存为WAV文件
output_file = "test_audio.wav"
with wave.open(output_file, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)  # 16-bit
    wf.setframerate(SAMPLE_RATE)
    # 转换为int16
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wf.writeframes(audio_int16.tobytes())

print(f"\n💾 已保存到 {output_file}")
print(f"   可以播放该文件检查音频质量")
