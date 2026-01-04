# Lumina - 智能桌面伴侣

Lumina 是一个先进的智能桌面伴侣应用，拥有生动的 Live2D 形象、实时语音交互能力以及桌面级功能。设计宗旨是作为你的桌面伙伴，倾听你的声音，并自然地与你互动。

![Lumina 预览图](https://via.placeholder.com/800x450?text=Lumina+AI+Preview)

## ✨ 核心功能

*   **Live2D 虚拟形象**: 完全可交互的动画角色，能响应触摸和鼠标移动（基于 N.E.K.O 技术）。
*   **实时语音交互**:
    *   **端侧 VAD (语音活动检测)**: 使用 `Silero VAD` 直接在浏览器（通过 WebAssembly）运行，实现超低延迟的语音检测。**不说话时绝不发送数据**，保护隐私且节省带宽。
    *   **自动语言识别**: 支持普通话（简体中文）和英语，自动切换。
*   **混合架构**:
    *   **前端**: Electron + React + Vite + TypeScript (提供极致 UI 体验)。
    *   **后端**: Python (FastAPI) 处理重型 AI 任务 (ASR, LLM)。
*   **隐私优先**: VAD 本地运行，只上传有效语音片段。API 密钥存储在本地 `.env` 文件中。

## 🛠️ 技术架构

Lumina 采用分离式架构以最大化性能和 UI 流畅度：

1.  **Electron (渲染层)**: 负责 Live2D 模型渲染、UI 展示以及音频采集 + 智能切片。
2.  **Python Server (后端)**: 运行 `faster-whisper` 进行语音转文字，并连接 AI 模型（DeepSeek 等）。
3.  **通信**: 使用高性能 WebSocket 连接进行音频流传输。

## 🚀 快速开始

### 环境要求

*   Node.js (v18+)
*   Python (v3.10+)
*   pnpm (推荐) 或 npm
*   FFmpeg (系统环境变量需包含，用于 Whisper 处理)

### 1. 安装

**前端:**
```bash
# 安装依赖
npm install

# 配置 VAD 资源 (通常会自动运行，如果 public/ 下缺文件请手动运行)
node scripts/copy-vad-assets.js
```

**后端:**
```bash
cd python_backend
# 创建虚拟环境 (可选但推荐)
python -m venv venv
# Windows: venv\Scripts\activate
# Linux/Mac: source venv/bin/activate

# 安装依赖
pip install -r requirements.txt
```

### 2. 配置

在根目录下创建 `.env` 文件：
```env
DEEPSEEK_API_KEY=your_api_key_here
```
*(注意: .env 文件已被 git 忽略，不会上传到仓库)*

### 3. 运行应用

需要同时运行后端和前端。
python python_backend/memory_server.py
.\start_lumina.ps1

**终端 1 (后端):**
```bash
cd python_backend
python stt_server.py
```
*(当看到 "Whisper model loaded successfully" 时即准备就绪)*

**终端 2 (前端):**
```bash
npm run dev
```

## 📦 技术栈

*   **核心**: Electron, React 18, TypeScript
*   **构建**: Vite
*   **AI/VAD**:
    *   前端: `@ricky0123/vad-react` (ONNX Runtime Web + Silero VAD)
    *   后端: `faster-whisper` (Python)
*   **Live2D**: Cubism SDK (via `pixi-live2d-display`)

## ⚠️ 常见问题 (Troubleshooting)

**"Failed to load resource: ... ort-wasm-simd-threaded.mjs"**
这是 Vite/Electron 的已知路径问题，我们已通过 alias 配置解决。只要在 Python 终端能看到 `Detected language` 日志，说明功能正常。

**"Unknown CPU vendor"**
这是 ONNX Runtime 在 WebAssembly 环境下的无害警告，请忽略。

## 📜 许可证

[MIT](LICENSE)
