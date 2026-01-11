# Lumina - 智能桌面伴侣

Lumina 是一个先进的智能桌面伴侣应用，拥有生动的 Live2D 形象、实时语音交互能力以及沉浸式的 GalGame 恋爱养成系统。她不仅能倾听你的声音，还能记住你的喜好，随着互动加深而建立羁绊。

![Lumina 预览图](https://via.placeholder.com/800x450?text=Lumina+AI+Preview)

## ✨ 核心功能

- **Live2D 沉浸交互**: 完全可交互的动画角色，能响应触摸、视线跟随，并根据情绪改变表情。
- **全链路语音交互**:
  - **STT (听)**: 本地化 Whisper/SenseVoice 模型，精准识别中英文。支持 VAD 自动断句。
  - **TTS (说)**: 集成 Edge TTS (在线) 和 GPT-SoVITS (本地)，声音自然动听，支持情感表达。
- **长短期记忆系统**:
  - **SurrealDB**: 存储对话历史、事实记忆和向量知识库。
  - **Dreaming Engine**: 在后台自动整理记忆、提取羁绊值，并模拟"做梦"来演化性格。
- **GalGame HUD**: 实时显示好感度、能量值、当前心情（Mood）和关系等级。
- **隐私优先**: 所有核心 AI 逻辑（STT/LLM/记忆）均可本地部署，API 密钥仅保存在本地。

## 🛠️ 技术架构

Lumina 采用分离式微服务架构以最大化性能：

1.  **Frontend (UI)**: Electron + React + Vite + TypeScript (Live2D 渲染, HUD, 音频采集).
2.  **Backend (Core)**: Python (FastAPI) 微服务集群:
    - `main.py`: 记忆服务 (SurrealDB 交互), Soul Management (性格演化).
    - `stt_server.py`: 语音识别 (Faster-Whisper/FunASR).
    - `tts_server.py`: 语音合成 (EdgeTTS/GPT-SoVITS).
3.  **User Flow**: 麦克风 -> 前端 VAD -> 后端 STT -> LLM (DeepSeek) -> 后端 TTS -> 前端播放.

## 🚀 快速开始 (Getting Started)

### 1. 环境准备 (Prerequisites)

请确保你的电脑已安装以下软件：

- **Node.js** (v18+): [下载](https://nodejs.org/)
- **Python** (v3.10 - v3.12): [下载](https://www.python.org/)
- **SurrealDB** (v2.0+): [下载与安装指南](https://surrealdb.com/install)
  - Windows (PowerShell): `iwr https://windows.surrealdb.com -useb | iex`
  - _必须确保 `surreal` 命令已添加到系统环境变量 PATH 中。_
- **FFmpeg**: [下载](https://ffmpeg.org/download.html)
  - 需将 `ffmpeg/bin` 添加到系统 PATH，用于音频转码。

---

### 2. 安装依赖 (Installation)

克隆项目后，打开终端执行以下步骤。

**Step A: 安装前端依赖**

```bash
npm install
```

**Step B: 安装后端依赖**

```bash
# 推荐创建虚拟环境
cd python_backend
python -m venv venv
# Windows 激活
venv\Scripts\activate
# Mac/Linux 激活
# source venv/bin/activate

# 安装 Python 库
pip install -r requirements.txt
```

**Step C: 配置 API Key**
在项目根目录创建 `.env` 文件，填入你的 LLM 服务商 Key (推荐 DeepSeek):

```env
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1
```

---

### 3. 启动应用 (Running)

我们提供了一键启动脚本（推荐）：

**Windows PowerShell:**

```powershell
.\start_lumina.ps1
```

_该脚本会自动检查 SurrealDB、启动 Python 后端集群、并运行 Electron 前端。_

---

### 🔧 手动启动模式 (Developer)

如果你需要分别调试各个服务，可以打开三个终端窗口：

**Terminal 1: 数据库**

```bash
surreal start --log info --user root --pass root --bind 0.0.0.0:8000 --allow-all file:lumina_surreal.db
```

**Terminal 2: Python 后端**

```bash
# 确保已激活 venv
cd python_backend
# 启动入口 (会自动拉起 STT/TTS 子进程)
python main.py
```

**Terminal 3: 前端**

```bash
npm run dev
```

## 📦 模型下载说明

应用首次启动时会尝试自动下载所需模型，但为了加速，你可以手动下载并放入 `python_backend/models/` 目录：

1.  **Embedding 模型**: `paraphrase-multilingual-MiniLM-L12-v2`
2.  **STT 模型**: `faster-whisper-small` (或其他尺寸)

## ⚠️ 常见问题 (Troubleshooting)

- **端口冲突 (Port 8000/8001/8765/8766 is busy)**:
  - 请检查是否有残留的 `python.exe` 或 `surreal.exe` 进程并结束它们。
- **Live2D 加载失败**:
  - 确保网络可以访问 GitHub (用于下载模型)，或手动下载 Live2D 模型放入 `public/live2d`。
- **声音无法播放**:
  - 检查系统音频输出设置。如果使用 GPT-SoVITS，确保已安装 FFmpeg。

## 📜 许可证

[MIT](LICENSE)
