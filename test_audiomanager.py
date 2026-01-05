"""
AudioManager最小化测试 - 移除所有VAD逻辑，纯录音
"""

from python_backend.audio_manager import AudioManager
import numpy as np
import wave
import time

print("=== AudioManager纯录音测试 ===")

audio_frames = []

def on_speech_end(audio_data):
    audio_frames.append(audio_data)
    print(f"收到音频: {len(audio_data)} samples, Range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")

# 创建AudioManager（但不用VAD）
manager = AudioManager(
    on_speech_start=None,
    on_speech_end=on_speech_end,
    on_vad_status_change=None
)

# 获取设备列表
devices = manager.list_devices()
print("\n可用设备:")
for dev in devices:
    print(f"  [{dev['index']}] {dev['name']}")

device_idx = int(input("\n选择设备索引: "))
manager.set_device(device_idx)

# 手动触发录音（绕过VAD）
print("\n准备录音5秒...")
input("按回车开始...")

recording = []

def simple_callback(indata, frames, time_info, status):
    if status:
        print(f"Status: {status}")
    audio_frame = indata[:, 0] if indata.ndim > 1 else indata
    recording.append(audio_frame.copy())

import sounddevice as sd

with sd.InputStream(
    device=device_idx,
    samplerate=16000,
    channels=1,
    dtype='float32',
    blocksize=480,
    callback=simple_callback
):
    print("录音中...")
    time.sleep(5)

print(f"录音完成！共 {len(recording)} 帧")

# 合并并分析
audio_data = np.concatenate(recording)
print(f"\n📊 音频统计:")
print(f"  样本数: {len(audio_data)}")
print(f"  Range: [{audio_data.min():.4f}, {audio_data.max():.4f}]")
print(f"  Mean: {audio_data.mean():.4f}, Std: {audio_data.std():.4f}")

# 保存
output_file = "audiomanager_test.wav"
with wave.open(output_file, 'wb') as wf:
    wf.setnchannels(1)
    wf.setsampwidth(2)
    wf.setframerate(16000)
    audio_int16 = (audio_data * 32767).astype(np.int16)
    wf.writeframes(audio_int16.tobytes())

print(f"\n💾 已保存到 {output_file}")
print("播放检查音质！")
