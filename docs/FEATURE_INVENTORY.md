# Feature Inventory

## 🏗️ 架构重构 (v2.0 - 2026-01-08)

- **状态**: ✅ 已模块化
- **后端** (`python_backend/`):
  - `main.py`: 入口文件，包含生命周期管理。
  - `routers/`: 5 个模块化路由（config, memory, characters, soul, debug）。
  - `schemas/requests.py`: Pydantic 数据模型。
- **前端** (`app/renderer/components/`):
  - `SettingsModal/`: 模块化设置面板，包含 4 个 Tab 组件。
  - 支持多角色切换（`activeCharacterId` 提升至 App.tsx）。

## 🧠 Memory System (SurrealDB Unified V3)

- **Status**: ✅ Operational / Production
- **Refactoring (2026-01)**: Removed `LiteMemory` (Qdrant/SQLite) in favor of pure SurrealDB.
- **Architecture**:
  - **Single Source of Truth**: SurrealDB (`./lumina_memory.db` via `surreal_memory.py`).
  - **Features**:
    - **Vector Search**: Integrated HNSW index in SurrealDB.
    - **Graph Relations**: Native graph support (`character` -> `observes` -> `fact`).
    - **Automated Digestion**: `Hippocampus` + `HeartbeatService` pipeline.
  - **Models**:
    - Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` loaded via `ModelManager`.
- **Legacy Status**:
  - `LiteMemory`, `Qdrant`, `SQLite` removed and archived (`python_backend/archive_legacy`).
  - `DreamingService` (Legacy) disabled.

## 🗄️ SurrealDB 集成（Graph Memory V1）

- **状态**: ✅ Operational (2026-01-08)
- **文件**: `surreal_memory.py`, `graph_curator.py`
- **架构文档**: [docs/KNOWLEDGE_GRAPH_MAINTENANCE.md](docs/KNOWLEDGE_GRAPH_MAINTENANCE.md)
- **功能**:
  - **向量搜索**: HNSW 索引 (384 维)，自动注入 `LiteMemory` 编码器复用资源。
  - **混合搜索**: Vector + FullText + Graph Search (1-hop 关系遍历)。
  - **知识图谱 (Knowledge Graph)**:
    - **实体消歧**: `_resolve_entity` 基于向量相似度自动合并同义实体。
    - **关系强化**: `add_knowledge_graph` 自动增强现有边权重 (`strength` += 0.05)。
  - **图谱维护 (The Gardener)**:
    - **生物衰减**: 读取查询自动应用时间衰减公式 (`strength` \* `0.99^days`).
    - **周期治理**: `heartbeat_service` 每 24h 触发 `graph_curator.py` 清除极弱连边。
- **安装要求**:
  - SurrealDB Server 2.0+ (支持向量索引)
  - 安装: `winget install SurrealDB.SurrealDB` 或从 [surrealdb.com](https://surrealdb.com/install) 下载
  - 启动: `surreal start --log info --user root --pass root memory`
  - 连接地址: `ws://127.0.0.1:8000/rpc`

## 🗣️ Voice System

- **Status**: ✅ Operational
- **Components**:
  - `stt_server.py`: Speech-to-Text (FunASR/SenseVoice).
  - `tts_server.py`: Text-to-Speech (CosyVoice & GPT-SoVITS).
    - **Optimization**: Implemented "Raw Stream Pipe" architecture. Requests PCM Stream from GPT-SoVITS and transcodes to AAC via local FFmpeg pipe for zero-latency MSE compatibility.
    - **Performance**: Added TTFB (Time To First Byte) & Chunk monitoring logs.
    - **Emotion Control**: Edge TTS 不支持情感样式；GPT-SoVITS 通过参考音频（`assets/emotion_audio/`）实现情感克隆。
  - `tts_service.ts` & `audio_queue.ts`: Frontend TTS Streaming Layer (Added dynamic chunk buffering and low-latency playback).

## 🎨 Live2D / Character System

- **Status**: ✅ Operational / Optimized
- **Components**:
  - `Live2DViewer.tsx`: Core model renderer.
  - `emotion_map.json`: Maps linguistic emotions (e.g. `happy`, `开心`) to model motion groups.
- **Features**:
  - **Motion Triggers**: LLM-driven `[emotion]` tags trigger animations (Priority 3 Force).
  - **Quiet Mode**: Custom 15s Idle Timer disables internal auto-motion to prevent interruptions.
  - **Tag Hiding**: `App.tsx` & `ChatBubble.tsx` strip `[tags]` from UI/TTS output.
  - **Multi-Character**: Support for multiple profiles, each with custom prompts (auto-injected system instructions).
- **Debugging**:
  - Enhanced emotion detection logging in `App.tsx` (processEmotions function).
  - Detailed logs for: buffer content, tag matches, emotion mapping, trigger status.
  - Support for Chinese parentheses「)」in emotion tags.
  - Test script: `test/emotion_test.ts`.
  - Debug guide: `.gemini/antigravity/brain/.../emotion_debug_guide.md`.

## 📝 Documentation

- `MEM0_ANALYSIS.md`: Detailed analysis of `mem0` library and persistence issues.
- `MEMORY_RESEARCH_REPORT.md`: In-depth research on 4 similar projects (Lunasia, Live2D, NagaAgent, MoeChat) comparing their memory architectures.

- **Voice Input**: Updated microphone icon to circular design with visual states (Ready/Listening/Thinking).
- **UI Design**: Applied flat layered design to Voice Input icon (Outer Ring + Inner Circle).
- **UI Design**: Simplified Voice Input icon to pure Glyph style (No background ring/circle).
- **UI Design**: Added Frosted Glass effect background to Voice Input icon.

## 📝 Prompt System (PromptManager V1)

- **Status**: ✅ Operational (2026-01-10)
- **Features**:
  - **PromptManager**: Unified template loader with Jinja2 support (`python_backend/prompt_manager.py`).
  - **Templates**: Storage in `python_backend/prompts/` (YAML/Text).
  - **Optimization**: Structured prompts for System (Chat) and Memory (Extract/Evolve) to reduce token usage and improve adherence.
