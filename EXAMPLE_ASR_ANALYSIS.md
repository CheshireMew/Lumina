# 开源项目语音识别 (ASR) 实现分析报告

本报告旨在深度分析 `example` 目录下 12 个开源项目的语音识别实现方式，为 Lumina 项目提供技术参考。

## 1. Live2D-Virtual-Girlfriend-main

- **文件**: `src/asr.py`
- **核心技术**:
  - **录音**: `pyaudio`
  - **VAD**: `webrtcvad` (自定义 `RealTimeVAD` 类，维护 `speech_buffer` 队列)
  - **ASR 模型**: 疑似 `SenseVoice` (调用 `Global.sense_voice.infer()`)
  - **声纹验证**: 集成，使用 `Global.speaker_verifier`
- **架构特点**:
  - 本地 Python 客户端，全栈式处理（录音、VAD、ASR、热词替换）。
  - 使用 `collections.deque` 做音频缓冲，逻辑清晰。
  - 热词替换逻辑简单直接。

## 2. MoeChat-main

- **文件**: `api/asr_api.py`
- **核心技术**:
  - **框架**: FastAPI
  - **协议**: WebSocket (`/asr_ws`)
  - **VAD**: `utils.pysilero` (Silero VAD)
  - **ASR**: 调用 `chat_core.asr` (具体模型待查)
- **架构特点**:
  - 典型的 C/S 架构，前端推流，后端识别。
  - 使用 Silero VAD 进行更鲁棒的语音活动检测。
  - 支持 Base64 编码的音频流。

## 3. ai_virtual_mate_web-main

- **文件**: `asr.py`
- **核心技术**:
  - **ASR**: `SenseVoiceSmall` (Sherpa-ONNX 离线版)
  - **VAD**: 基于 RMS 能量的简单门限检测 (非 AI 模型)
  - **声纹**: `3D-Speaker CAM++` (Sherpa-ONNX)
- **架构特点**:
  - **Golden Sample**: 这是与我们目标最接近的实现。
  - **情感解析**: 代码中完整实现了对 `<HAPPY>`, `<SAD>` 等 SenseVoice 特有标签的解析。
  - **一体化**: 在一个文件中集成了 录音 -> VAD -> 声纹 -> ASR。

## 4. Lunar-Astral-Agents-master

- **文件**: `script/SpeechAPI/code.ts`
- **核心技术**: 纯前端 `window.SpeechRecognition` (Webkit)
- **架构特点**: 完全依赖浏览器能力，无后端 ASR 成本。

## 5. N.E.K.O-main

- **文件**: `main_logic/core.py`
- **核心技术**: `OmniRealtimeClient` (API Wrapper)
- **架构特点**: 将语音视为多模态流的一部分，直接发给大模型，没有独立的 ASR 步骤。

## 5. My-Neuro-main

- **文件**: `full-hub/asr_api.py`
- **核心技术**: **FunASR** (阿里摩搭 ModelScope)
- **关键实现**:
  - **ASR 模型**: `Paraformer-Large` (非自回归模型，速度极快)
  - **VAD**: `Silero VAD` (PyTorch Hub 本地加载)
  - **标点恢复**: `CT-Transformer`
- **特点**: 这是一个工业级的 ASR 服务实现，使用了双重日志记录和完善的模型下载逻辑。与 SenseVoice 不同，Paraformer 更专注于精准的文字转写，不包含情感识别。

## 6. Ten-Framework-main

- **核心技术**: Agora (声网) RTC SDK
- **架构特点**: 这是一个实时音视频框架 (RTC)，主要解决音频的低延迟传输和回声消除 (AEC)，而非各种本地 ASR。它通常对接云端 ASR 服务。

## 7. ZcChat-main

- **核心技术**: C++ / Qt Multimedia
- **架构特点**: 桌面端原生实现，调用系统级录音接口。

## 8. Nana-main & Super-Agent-Party-main

- **核心技术**: 云端 API (OpenAI/Azure)
- **架构特点**: 这些主要是 Agent 编排框架，语音部分并非重点，通常通过配置 API Key 调用云服务，代码中没有复杂的本地音频处理逻辑。

## 9. NagaAgent-main

- **核心技术**: (未发现本地 ASR)
- **架构特点**: 同样是一个 Agent 框架，依赖外部语音服务接口。

## 10. deepseek-Lunasia-2.0-main

- **核心技术**: 无本地 ASR
- **架构特点**: 纯文本对话或依赖 API。

## 💡 总结与建议

1. **SenseVoice 最佳参考**: `ai_virtual_mate_web-main` 提供了非常完美的 `Sherpa-ONNX + SenseVoice` 集成代码，特别是情感标签解析部分（Line 134-140）可以直接复用于 Lumina。
2. **架构选型**:
   - 如果追求**情感交互**，SenseVoice (如 `ai_virtual_mate_web`) 是唯一选择。
   - 如果追求**极致转写精度**，Paraformer (如 `my-neuro`) 是很好的备选。
3. **VAD 升级**: 我们可以考虑引入 `Silero VAD` (参考 `MoeChat` 或 `my-neuro`) 来替代目前的 `webrtcvad`，因为它对背景噪音的过滤能力更强。
