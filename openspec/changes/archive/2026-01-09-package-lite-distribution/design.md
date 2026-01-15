# Design: Lumina Lite Packaging Architecture

## Architecture Overview

传统的 Python/Electron 应用分发通常面临环境地狱。本设计采用 "**Compiled Backend + Bundled Binaries**" 模式。

### 1. The "Sidecar" Pattern

Electron (Main Process) 充当 Process Manager,不再依赖用户系统中的 Python 环境。

- **Before (Dev)**:
  `Electron` -> `spawn("python", ["main.py"])` -> `System Python Environment`

- **After (Prod)**:
  `Electron` -> `spawn("resources/backend/lumina_backend.exe")` -> `Self-contained Runtime`

### 2. Dependency Management Strategy

为了实现 <500MB 的目标,必须激进地剪裁依赖。

| 组件    | Dev 依赖                      | Prod (Lite) 策略                                                      |
| :------ | :---------------------------- | :-------------------------------------------------------------------- |
| **STT** | Faster-Whisper (Large) + CUDA | **Sherpa-ONNX (SenseVoice)** + CPU Only. 移除 Torch CUDA DLLs (~2GB). |
| **TTS** | GPT-SoVITS + CUDA             | **Edge TTS** (Online). 移除 GPT-SoVITS 及其模型。                     |
| **LLM** | Ollama / Local Transformers   | **OpenAI Compatible Client**. 不打包任何 LLM 模型。                   |
| **DB**  | SurrealDB System Service      | **Embedded SurrealDB Binary**. Electron 负责启动和关闭。              |

### 3. File System Layout (In Installer)

```text
/Lumina-Lite/
  ├── lumina.exe          (Electron Launcher)
  ├── resources/
  │   ├── app.asar        (Frontend Code)
  │   └── bin/
  │       ├── lumina_backend.exe
  │       ├── surreal.exe
  │       ├── ffmpeg.exe
  │       └── assets/
  │           └── sense-voice/ (Pre-bundled quantized model)
```

## Risks & Mitigations

1.  **Anti-Virus False Positives**: PyInstaller 打包的 exe 常被误报。
    - _Mitigation_: 使用干净环境编译,提交给 Microsoft 分析,或提示用户添加白名单。
2.  **Path Resolution**: `_MEIPASS` 临时目录路径问题。
    - _Mitigation_: 在 Python 后端代码中添加 `sys.frozen` 检测逻辑,动态修正资源路径。
