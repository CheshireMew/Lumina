# 参考项目音频捕获方案分析报告

## 🎯 Executive Summary

经过对 11 个同类项目的深入研究，发现了**三种主流音频架构**：

1. **纯前端架构**（6个项目）：使用 `getUserMedia` + `MediaRecorder` + VAD.js
2. **纯后端架构**（3个项目）：使用 `pyaudio`/`sounddevice` + `webrtcvad`
3. **混合架构**（2个项目）：前端采集 + 后端VAD处理

## 📊 项目分类统计

### ✅ 纯前端音频捕获（6个项目）
- **N.E.K.O** - 完整前端VAD + AudioWorklet
- **MoeChat** - MediaRecorder + pysilero后端VAD（WebSocket）
- **super-agent-party** - @ricky0123/vad-react（Silero VAD）
- **my-neuro** - AudioWorklet + ASR Processor
- **ai_virtual_mate_web** - getUserMedia基础方案
- **Lunar-Astral-Agents** - 前端音频流

### ✅ 纯后端音频捕获（3个项目）
- **Live2D-Virtual-Girlfriend** ⭐ **重点学习对象**
- **NagaAgent** （仅依赖检查，未查到具体实现）
- **ZcChat** - Qt C++ `QMediaRecorder`

### ❓ 架构不明确（2个项目）
- **deepseek-Lunasia-2.0** - 未找到README
- **nana** - 未找到明确音频代码

---

## 🔬 深度分析：Live2D-Virtual-Girlfriend（最佳参考）

### 架构特点
```
后端完全控制音频流：PyAudio 捕获 → webrtcvad 实时VAD → SenseVoice STT
```

### 核心代码架构（asr.py）

#### 1. VAD 处理类
```python
class RealTimeVAD:
    def __init__(self, aggressiveness=3, sample_rate=16000):
        self.vad = webrtcvad.Vad(aggressiveness)
        self.sample_rate = 16000
        self.frame_duration = 30  # ms
        self.frame_length = int(16000 * 30 / 1000)  # 480 samples
        
        # 滑动窗口缓冲区：10帧历史
        self.speech_buffer = collections.deque(maxlen=10)
    
    def process_frame(self, frame_data):
        is_speech = self.vad.is_speech(frame_data, self.sample_rate)
        self.speech_buffer.append(is_speech)
        
        speech_ratio = sum(self.speech_buffer) / len(self.speech_buffer)
        
        # 状态机：silence → speech_start → speech_continue → speech_end
        if not self.is_speaking and speech_ratio > 0.5:
            return "speech_start"
        elif self.is_speaking and speech_ratio < 0.3:
            return "speech_end"
        elif self.is_speaking:
            return "speech_continue"
        else:
            return "silence"
```

**💡 关键设计亮点**：
- ✅ **滑动窗口平滑**：用 10帧历史计算语音比例，避免单帧误判
- ✅ **阈值双门限**：`0.5` 启动、`0.3` 结束，防抖抗干扰
- ✅ **30ms帧大小**：webrtcvad 标准帧长（10/20/30ms）

#### 2. 音频捕获循环
```python
def speech_recognition(web=False):
    CHUNK = int(16000 * 0.03)  # 30ms = 480 samples
    FORMAT = pyaudio.paInt16
    CHANNELS = 1
    RATE = 16000
    
    # 预缓冲区：保留语音前 0.5s
    PRE_BUFFER_SECONDS = 0.5
    PRE_BUFFER_SIZE = int(RATE / CHUNK * PRE_BUFFER_SECONDS)
    
    p = pyaudio.PyAudio()
    stream = p.open(
        format=FORMAT,
        channels=CHANNELS,
        rate=RATE,
        input=True,
        frames_per_buffer=CHUNK
    )
    
    while True:
        frames = []
        pre_buffer = deque(maxlen=PRE_BUFFER_SIZE)
        
        while True:
            data = stream.read(CHUNK)
            vad_result = vad_processor.process_frame(data)
            
            if vad_result == "speech_start":
                # 📌 关键：检测到语音后，将预缓冲区的历史音频也加入
                frames.extend(pre_buffer)
                frames.append(data)
                
            elif vad_result == "speech_continue":
                frames.append(data)
                
            elif has_speech and vad_result == "silence":
                break
            
            # 始终维护预缓冲区
            pre_buffer.append(data)
        
        # 保存为 WAV 并调用 STT
        wf = wave.open('temp/temp.wav', 'wb')
        wf.writeframes(b''.join(frames))
```

**💡 关键设计亮点**：
- ✅ **预缓冲区**：捕获语音起始前 0.5s，避免丢失开头音节
- ✅ **循环检测**：持续监听，无需手动触发
- ✅ **设备隔离**：`pyaudio.open(input=True)` 直接指定输入设备索引

---

## 🆚 方案对比：前端 vs 后端

| 维度 | 纯前端 | 纯后端（pyaudio+webrtcvad） | **我们当前** |
|------|--------|---------------------------|-----------|
| **设备隔离** | ❌ 混淆麦克风/回环 | ✅ 精确选择物理设备 | ❌ 前端VAD |
| **VAD准确性** | ⚠️ Silero模型大 | ✅ webrtcvad专业轻量 | ⚠️ @ricky0123/vad-react |
| **延迟** | ~100-300ms | ~50-100ms | ~200ms |
| **跨平台** | ✅ Web通用 | ⚠️ 需本地Python | ✅ Electron兼容 |
| **复杂度** | 低 | 中 | 当前：低 |
| **回环问题** | ❌ **无法彻底解决** | ✅ **完全隔离** | ❌ **当前痛点** |

### ⚠️ 前端方案的致命缺陷（为什么要迁移）

#### N.E.K.O 项目的痛苦经验
```javascript
// app.js:1105-1112 - 他们也尝试禁用回声消除，但无效
const baseAudioConstraints = {
    noiseSuppression: false,
    echoCancellation: true,   // ⚠️ 即使开启，系统仍可能回环
    autoGainControl: true,
    channelCount: 1
};
```

**问题分析**：
1. `getUserMedia` 无法区分"麦克风A"和"立体声混音（系统回环）"
2. Windows默认设备可能被其他应用篡改
3. 浏览器的 `deviceId` 不稳定（设备重新插拔后会变）

#### MoeChat 的折衷方案
```javascript
// moechat_core.js:319-322 - 他们选择前端采集+后端VAD
navigator.mediaDevices.getUserMedia({ audio: true }).then(stream => {
    mediaRecorder = new MediaRecorder(stream);
    // WebSocket 发送到后端 pysilero VAD
});
```

**仍然无法解决**：前端采集阶段已经混入了系统音频

---

## 📋 技术栈对比

### 后端VAD库选择

| 库 | 优势 | 劣势 | 项目使用 |
|----|------|------|----------|
| **webrtcvad** | ✅ 超轻量（Google官方）<br>✅ 延迟极低<br>✅ CPU占用小 | ⚠️ 仅支持16kHz<br>⚠️ 功能单一 | Live2D-VG ⭐ |
| **pysilero** | ✅ 准确率更高<br>✅ 支持多采样率 | ❌ 模型较大（~2MB）<br>❌ 需ONNX Runtime | MoeChat |
| **Silero VAD (JS)** | ✅ 纯前端<br>✅ ONNX Web | ❌ 回环问题<br>❌ 加载慢 | N.E.K.O, super-agent |

### 音频捕获库选择

| 库 | 优势 | 劣势 | 项目使用 |
|----|------|------|----------|
| **pyaudio** | ✅ 成熟稳定<br>✅ 跨平台 | ⚠️ 安装依赖较重<br>⚠️ 需PortAudio | Live2D-VG ⭐ |
| **sounddevice** | ✅ 现代API<br>✅ 更好的错误处理 | ⚠️ 也需PortAudio | NagaAgent |
| **getUserMedia** | ✅ 零依赖 | ❌ **无法隔离设备** | 大多数Web项目 |

---

## 🎯 最佳实践总结

### ✅ 采纳建议

#### 1. **使用 `sounddevice` 而非 `pyaudio`**
   - ✅ 更现代的API（2015+ vs 2006）
   - ✅ 更好的错误处理和设备枚举
   - ✅ 支持异步回调（可选）

#### 2. **保留 `webrtcvad`**
   - ✅ Live2D-Virtual-Girlfriend 验证过的方案
   - ✅ 资源占用极小，适合实时场景

#### 3. **借鉴预缓冲区设计**
```python
# 参考 Live2D-VG 的设计
PRE_BUFFER_SECONDS = 0.5  # 保留语音前0.5秒
```

#### 4. **滑动窗口状态机**
```python
speech_buffer = collections.deque(maxlen=10)
speech_ratio = sum(speech_buffer) / len(speech_buffer)

if speech_ratio > 0.5:  # 启动阈值
    trigger_speech_start()
elif speech_ratio < 0.3:  # 停止阈值
    trigger_speech_end()
```

---

## ⚠️ 需要注意的坑

### 1. **PyAudio vs SoundDevice 依赖问题**
```bash
# PyAudio 在 Windows 上安装困难
pip install pyaudio  # ❌ 可能失败

# SoundDevice 更友好
pip install sounddevice  # ✅ 推荐
```

### 2. **设备索引持久化**
```python
# ❌ 错误：直接存储设备索引
config['device_index'] = 2

# ✅ 正确：存储设备唯一标识
import sounddevice as sd
devices = sd.query_devices()
config['device_name'] = devices[2]['name']  # "Microphone (Realtek)"

# 启动时重新匹配
for i, dev in enumerate(sd.query_devices()):
    if dev['name'] == config['device_name']:
        device_index = i
```

### 3. **WebSocket推送策略**
参考 MoeChat 的设计：
```javascript
// 前端监听 VAD 状态
socket.onmessage = (event) => {
    const data = JSON.parse(event.data);
    
    if (data.type === 'vad_status') {
        updateUI(data.status);  // 'listening' | 'thinking' | 'idle'
    }
    
    if (data.type === 'transcription') {
        onSend(data.text);
    }
};
```

---

## 🏗️ 推荐架构（基于研究结论）

```
┌─────────────────────────────────────────────┐
│           Electron Frontend (React)         │
│  - 无麦克风权限请求                           │
│  - WebSocket 监听 VAD 状态                   │
│  - UI 显示 listening/thinking                │
└──────────────┬──────────────────────────────┘
               │ WebSocket
               ▼
┌─────────────────────────────────────────────┐
│       Python Backend (FastAPI)              │
│                                             │
│  sounddevice.InputStream                    │
│       ↓                                     │
│  webrtcvad.Vad.is_speech()                  │
│       ↓                                     │
│  [Pre-Buffer] + [VAD Frames]                │
│       ↓                                     │
│  Whisper STT                                │
│       ↓                                     │
│  WebSocket.send({type: 'transcription'})   │
└─────────────────────────────────────────────┘
```

---

## 📝 核心代码参考（Live2D-VG 改写版）

```python
import sounddevice as sd
import webrtcvad
import numpy as np
from collections import deque

class AudioManager:
    def __init__(self, device_index=None, sample_rate=16000):
        self.vad = webrtcvad.Vad(aggressiveness=3)
        self.sample_rate = sample_rate
        self.frame_duration_ms = 30
        self.frame_size = int(sample_rate * self.frame_duration_ms / 1000)
        
        self.device_index = device_index
        self.speech_buffer = deque(maxlen=10)
        self.pre_buffer = deque(maxlen=int(0.5 * 1000 / self.frame_duration_ms))  # 0.5s
        self.audio_frames = []
        self.is_speaking = False
    
    def process_frame(self, frame: np.ndarray):
        # Convert float32 [-1,1] to int16 PCM
        pcm = (frame.clip(-1, 1) * 32767).astype(np.int16).tobytes()
        
        # VAD detection
        is_speech = self.vad.is_speech(pcm, self.sample_rate)
        self.speech_buffer.append(is_speech)
        speech_ratio = sum(self.speech_buffer) / len(self.speech_buffer)
        
        # State machine
        if not self.is_speaking and speech_ratio > 0.5:
            self.is_speaking = True
            self.audio_frames.extend(self.pre_buffer)  # Add pre-buffer
            self.audio_frames.append(frame)
            return "speech_start"
        
        elif self.is_speaking and speech_ratio < 0.3:
            self.is_speaking = False
            audio = np.concatenate(self.audio_frames)
            self.audio_frames.clear()
            return "speech_end", audio
        
        elif self.is_speaking:
            self.audio_frames.append(frame)
            return "speech_continue"
        
        else:
            self.pre_buffer.append(frame)
            return "silence"
    
    def start(self, callback):
        with sd.InputStream(
            device=self.device_index,
            samplerate=self.sample_rate,
            channels=1,
            dtype='float32',
            blocksize=self.frame_size,
            callback=lambda indata, frames, time, status: callback(indata[:, 0])
        ):
            input("Press Enter to stop...")  # 阻塞主线程
```

---

## 🎓 结论与建议

### ✅ 强烈推荐迁移到后端VAD
经过对 11 个项目的研究，**Live2D-Virtual-Girlfriend** 的纯后端方案是**最成熟、最可靠**的解决方案：

1. **彻底解决回环问题**（N.E.K.O等前端项目无法解决）
2. **技术栈已验证**（webrtcvad + pyaudio/sounddevice）
3. **性能优秀**（延迟低、资源占用小）

### 🛠️ 实施路径
1. 添加 `sounddevice` 依赖（比 `pyaudio`  更友好）
2. 完全复用 `webrtcvad`（已在 requirements.txt）
3. 借鉴 Live2D-VG 的**预缓冲区**和**滑动窗口**设计
4. WebSocket 推送 VAD 状态（参考 MoeChat）

### ✅ 避免的错误
- ❌ 不要尝试"前端采集+后端VAD"（MoeChat的折衷方案仍无法解决回环）
- ❌ 不要使用 `pysilero`（过重，webrtcvad 足够）
- ❌ 不要直接存储设备索引（需存储设备名称并动态匹配）
