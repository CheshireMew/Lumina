# Lumina - 智能桌面伴侣

Lumina 是一个先进的智能桌面伴侣应用，拥有生动的 Live2D 形象、实时语音交互能力以及沉浸式的 GalGame 恋爱养成系统。她不仅能倾听你的声音，还能记住你的喜好，随着互动加深而建立羁绊。

## ✨ 核心功能

- **Live2D 沉浸交互**: 完全可交互的动画角色，能响应触摸、视线跟随，并根据情绪改变表情。
- **全链路语音交互**:
  - **STT (听)**: 本地化 SenseVoice 模型，精准识别中英日多语言。支持 VAD 自动断句。
  - **TTS (说)**: 集成 Edge TTS (在线) 和 GPT-SoVITS (本地)，声音自然动听，支持情感表达。
- **长短期记忆系统**:
  - **PostgreSQL + pgvector**: 存储对话历史、事实记忆和向量知识库。
  - **Dreaming Engine**: 在后台自动整理记忆、提取羁绊值，并模拟"做梦"来演化性格。
- **GalGame HUD**: 实时显示好感度、能量值、当前心情(Mood)和关系等级。
- **隐私优先**: 所有核心 AI 逻辑(STT/LLM/记忆)均可本地部署，API 密钥仅保存在本地。

---

## 🛠️ 技术架构

Lumina 采用**分布式微服务架构**以最大化性能与可扩展性:

```
┌─────────────────────────────────────────────────────────────┐
│                    Electron + React + Vite                  │
│              (Live2D 渲染, HUD, 音频采集, 安全沙箱)          │
└───────────────────────────┬─────────────────────────────────┘
                            │ IPC / HTTP
┌───────────────────────────┴─────────────────────────────────┐
│                  Python FastAPI 微服务集群                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────┐  │
│  │ Memory (8010)│  │ STT (8765) │  │ TTS (8766)          │  │
│  │ Chat/Soul    │  │ SenseVoice │  │ EdgeTTS/GPT-SoVITS  │  │
│  └─────────────┘  └─────────────┘  └─────────────────────┘  │
│                            │                                 │
│  ┌─────────────────────────┴─────────────────────────────┐  │
│  │              PostgreSQL + pgvector                     │  │
│  │         (LifecycleBus, Memory, Plugin State)           │  │
│  └────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────┘
```

### 核心组件

| 服务            | 端口   | 职责                                 |
| :-------------- | :----- | :----------------------------------- |
| **Memory/Core** | `8010` | 对话、记忆、Soul 管理、插件协调      |
| **STT Server**  | `8765` | 语音识别 (SenseVoice/Whisper)        |
| **TTS Server**  | `8766` | 语音合成 (EdgeTTS/GPT-SoVITS)        |
| **PostgreSQL**  | `5432` | 持久化存储、向量检索、分布式状态同步 |

---

## 🚀 快速开始

### 1. 环境准备

请确保你的电脑已安装以下软件:

- **Node.js** (v18+): [下载](https://nodejs.org/)
- **Python** (v3.10 - v3.12): [下载](https://www.python.org/)
- **PostgreSQL** (v15+): [下载](https://www.postgresql.org/download/)
  - 需要安装 `pgvector` 扩展用于向量检索
- **FFmpeg**: [下载](https://ffmpeg.org/download.html)
  - 需将 `ffmpeg/bin` 添加到系统 PATH，用于音频转码

### 2. 数据库配置

```sql
-- 创建数据库和用户
CREATE DATABASE lumina_db;
CREATE USER lumina_app WITH PASSWORD 'your_password';
GRANT ALL PRIVILEGES ON DATABASE lumina_db TO lumina_app;

-- 安装 pgvector 扩展 (需要超级用户)
\c lumina_db
CREATE EXTENSION IF NOT EXISTS vector;
```

### 3. 安装依赖

**Step A: 前端依赖**

```bash
npm install
```

**Step B: 后端依赖**

```bash
cd python_backend
python -m venv venv
# Windows
venv\Scripts\activate
# Mac/Linux
# source venv/bin/activate

pip install -r requirements.txt
```

**Step C: 配置环境变量**

在项目根目录创建 `.env` 文件:

```env
# LLM 配置 (推荐 DeepSeek 或 Gemini)
DEEPSEEK_API_KEY=sk-xxxxxxxxxxxxxxxxxxxxxxxx
DEEPSEEK_BASE_URL=https://api.deepseek.com/v1

# PostgreSQL (可选，默认值见 config/lumina_config.yaml)
# LUMINA_PG_HOST=localhost
# LUMINA_PG_PORT=5432
# LUMINA_PG_USER=lumina_app
# LUMINA_PG_PASSWORD=your_password
# LUMINA_PG_DATABASE=lumina_db
```

### 4. 启动应用

**一键启动 (推荐):**

```powershell
.\start_lumina.ps1
```

**手动启动 (开发者模式):**

```bash
# Terminal 1: PostgreSQL (如果未作为服务运行)
# pg_ctl start -D /path/to/data

# Terminal 2: Python 后端
cd python_backend
python main.py

# Terminal 3: 前端
npm run dev
```

---

## 🧩 插件系统 (Plugin System V3)

Lumina 采用**混合微内核架构**，核心功能通过插件实现:

### 内置插件

| 插件                 | 类型      | 功能                       |
| :------------------- | :-------- | :------------------------- |
| **HeartbeatManager** | Extension | 主动聊天 + 番茄钟          |
| **GalgameManager**   | Extension | 恋爱养成系统 (好感度/能量) |
| **DreamingManager**  | Extension | "做梦"记忆整合             |
| **EvolutionManager** | Extension | 灵魂/性格演化              |
| **WebSearchTool**    | Tool      | 联网搜索能力               |

### 驱动插件 (Worker Plugins)

| 驱动                      | 运行进程 | 功能                |
| :------------------------ | :------- | :------------------ |
| **driver.stt.sensevoice** | STT      | SenseVoice 语音识别 |
| **driver.tts.edge**       | TTS      | Edge TTS 语音合成   |

### 插件开发

插件放入 `python_backend/plugins/` 目录即可自动加载:

```
plugins/
├── system/           # 系统级插件 (需要 manifest.yaml)
├── extensions/       # 扩展插件 (可选 manifest.yaml)
└── drivers/          # 驱动插件 (STT/TTS 等)
    └── stt/
        └── sensevoice/
            ├── manifest.yaml
            └── driver.py
```

**Manifest 示例:**

```yaml
id: my_plugin
name: My Plugin
version: 1.0.0
permissions:
  - network.outbound
  - filesystem.read
```

详细开发文档见 [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)。

---

## 🧪 测试

Lumina 拥有完善的自动化测试体系:

```bash
# 运行所有后端测试
pytest automation/tests_pytest/ -v

# 运行性能基准测试
pytest automation/tests_pytest/performance/ -v --benchmark-only

# 运行前端单元测试
npx vitest run
```

### 测试类型

| 类型            | 目录                                   | 说明                   |
| :-------------- | :------------------------------------- | :--------------------- |
| **Backend**     | `automation/tests_pytest/backend/`     | 后端服务单元/集成测试  |
| **E2E**         | `automation/tests_pytest/e2e/`         | 端到端 API 测试        |
| **Performance** | `automation/tests_pytest/performance/` | 压力测试、内存泄漏检测 |
| **Chaos**       | `automation/tests_pytest/chaos/`       | 故障注入、资源耗尽测试 |
| **Frontend**    | `app/renderer/**/*.test.tsx`           | React 组件 Vitest 测试 |

---

## 📦 模型下载

应用首次启动时会尝试自动下载所需模型，也可手动下载放入 `python_backend/models/`:

- **Embedding**: `paraphrase-multilingual-MiniLM-L12-v2`
- **STT**: `SenseVoiceSmall` (推荐) 或 `faster-whisper-small`

---

## ⚠️ 常见问题

- **端口冲突 (8010/8765/8766)**:
  - 检查并结束残留的 `python.exe` 进程
- **PostgreSQL 连接失败**:
  - 确保 PostgreSQL 服务已启动
  - 检查 `config/lumina_config.yaml` 中的凭据配置
- **Live2D 加载失败**:
  - 确保网络可访问 GitHub，或手动下载模型放入 `public/live2d`

---

## 🏗️ 架构参考

- **[ARCHITECTURE.md](docs/ARCHITECTURE.md)** - 系统架构概览
- **[FEATURE_INVENTORY.md](FEATURE_INVENTORY.md)** - 功能清单
- **[REPO_MAP.md](docs/REPO_MAP.md)** - 代码库导航图

---

## 🗺️ 路线图

### 已完成 ✅

- [x] Live2D 沉浸交互
- [x] 全链路语音交互 (STT/TTS)
- [x] PostgreSQL + pgvector 记忆系统
- [x] GalGame HUD 界面
- [x] 插件系统 V3 (Manifest 驱动 + 权限隔离)
- [x] EventBus 事件总线
- [x] 分布式状态同步 (LifecycleBus)
- [x] 自动化测试体系 (Pytest + Vitest + Chaos)

### 进行中 🚧

- [ ] 插件热加载/卸载
- [ ] 第三方插件市场
- [ ] 多模型路由优化

### 规划中 📋

- [ ] 插件沙箱隔离
- [ ] 多角色支持
- [ ] 跨平台 (macOS/Linux)

---

## 📜 许可证

[MIT](LICENSE)
