# 功能清单 (Feature Inventory)

## 核心架构

- **前端**: Electron + React + TypeScript + Vite.
- **后端**: Python (FastAPI) + Uvicorn.
- **数据库**: SurrealDB (图/向量数据库), SQLite (旧版/备份).
- **通信**: HTTP REST + WebSocket.

## 模块详解

### 1. 音频系统 (Audio System)

- **STT (语音转文字)**:
  - 独立服务进程 (`stt_server.py`).
  - 引擎: SenseVoice, Paraformer.
  - 配置: `stt_config.json`.
- **TTS (文字转语音)**:
  - 独立服务进程 (`tts_server.py`).
  - 引擎: GPT-SoVITS.
  - 前端队列: `audio_queue.ts` (顺序播放).
- **VAD (语音活动检测)**:
  - 已迁移至后端 (`audio_manager.py`).
  - 前端 `VoiceInput` 组件负责可视化状态。

### 2. 角色系统 (`soul_manager.py`)

- **档案**: 存储在 `characters/{id}/` 目录.
- **Live2D**: 前端 `Live2DViewer` 组件.
- **情感引擎 (Emotion Engine)**:
  - 文字转情感映射 (`emotion_map.json`).
  - Live2D 动作触发.
  - 灵魂变异 (Soul Mutation, 能量/亲密度属性).

### 3. 记忆系统 (`memory/`)

- **结构**: 3 层记忆架构 (短期/中期/长期).
- **存储**: SurrealDB.
- **特性**:
  - 混合搜索 (向量 + 关键词).
  - 自动摘要 (Auto-summarization).
  - "做梦"机制 (Dreaming, 离线整合/反思).

### 4. 交互循环 (Interaction Loop)

- **主动聊天 (Proactive Chat)**:
  - 后端状态监控 (`galgame/{id}/state`).
  - 前端轮询 (5 秒间隔).
  - 逻辑: 检测沉默 -> 基于记忆/上下文触发话题.
- **聊天界面**:
  - 文本输入.
  - 语音输入 (麦克风).
  - 使用 "ChatBubbles" 渲染历史记录.

## 架构审查发现的问题

- **前端复杂度高**: `App.tsx` 承担了太多职责 (UI, 业务逻辑, 网络请求)，甚至被称为 "God Component"。
- **硬编码**: API URL 在前端组件中到处都是 (`localhost:8001`)。
- **并发管理**: 需要开启多个后端终端才能完整运行 (Main, STT, TTS)。

## 路线图 (Roadmap)

- [ ] 重构前端 Hooks (拆分 App.tsx).
- [ ] 统一后端启动器.
- [ ] 优化 SurrealDB 连接处理.
