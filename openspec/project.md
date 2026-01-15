# 项目上下文:Lumina (AI Galgame Memory System)

## 目的

Lumina 是一个本地优先、注重隐私的 AI 伴侣记忆系统,主要服务于 Galgame 角色(如 "Hiyori")。
核心目标是通过**知识图谱 (Knowledge Graph)** 和 **向量检索 (Vector Search)** 实现长期、连贯且具有情感深度的情节记忆与语义记忆。
系统旨在解决 LLM "灾难性遗忘" 问题,并支持多模态交互(语音、Live2D 动作)。

## 技术栈

### 后端 (Python 3.12+)

- **框架**: FastAPI (ASGI), Uvicorn
- **数据库**:
  - **SurrealDB** (Websocket/RPC): 核心知识图谱存储,支持图关系与混合检索。
  - **Qdrant** / **LiteMemory** (SQLite): 向量索引(逐步迁移至 SurrealDB)。
- **AI 模型**:
  - **LLM**: DeepSeek (OpenAI 兼容 API) / ZhipuGLM。
  - **由文本转语音 (TTS)**: CosyVoice / GPT-SoVITS (本地 API, 动态流式传输)。
  - **语音转文本 (STT)**: FunASR / SenseVoice (本地)。
  - **Embeddings**: SentenceTransformers (`paraphrase-multilingual-MiniLM-L12-v2`).
- **依赖管理**: `requirements.txt` (或 Python 虚拟环境).

### 前端 (Web App)

- **框架**: React 18, Vite, TypeScript
- **样式**: TailwindCSS, Lucide React (图标)
- **交互**: Live2D (Cubism SDK), WebSocket (实时通信)

## 项目约定

### 代码风格

- **Python**: 遵循 PEP 8。使用 Type Hints (`typing`). Pydantic 模型用于所有数据交换。
- **TypeScript**: 强类型,使用 Functional Components 和 Hooks。
- **命名**:
  - Python: `snake_case` (变量/函数), `PascalCase` (类).
  - TS/React: `camelCase` (变量/函数), `PascalCase` (组件).
  - 文件名: Python 使用 `snake_case.py`,React 组件使用 `PascalCase.tsx`。

### 架构模式

- **模块化单体**: 后端按功能拆分 Router (`routers/`) 和 Service (`*_server.py`, `*_service.py`)。
- **双层记忆架构**:
  1. **Short-term**: 内存/Redis (暂未使用).
  2. **Long-term**:
     - **Episodic**: 向量数据库 (Qdrant).
     - **Semantic**: 知识图谱 (SurrealDB `entity` -> `relation` -> `entity`).
- **本地优先**: 尽量避免外部 API 依赖(LLM 除外),TTS/STT 均为本地部署。

### 提交约定

- 此项目尚未使用严格的 Conventional Commits,但建议使用: `feat:`, `fix:`, `docs:`, `refactor:`.

## 领域上下文

- **Hiyori (日和)**: 主要 AI 角色,性格设定为 "傲娇" (Tsundere),喜欢 "红茶" (Black Tea),讨厌 "孤独"。
- **SurrealDB ID**: 实体 ID 格式为 `entity:Name` (或 `entity:⟨Name⟩` 对于非 ASCII)。
- **Conflict Resolution**: `GraphCurator` 负责定期清理冲突事实(目前基于规则,计划引入语义仲裁)。

## 重要约束

- **Windows**: 开发环境为 Windows 11,需注意路径分隔符与 PowerShell 指令。
- **性能**: TTS 必须低延迟(<1s TTFB)。
- **隐私**: 对话日志存储在本地,不上传云端。

## 外部依赖

- SurrealDB Server (Local `ws://127.0.0.1:8000`)
- DeepSeek API (External)
- FunASR/CosyVoice Servers (Local Python Processes)
