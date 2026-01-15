# 功能清单 (Feature Inventory)

> Last Updated: 2026-01-15 (Architecture Refactor Complete)

## 1. 核心架构 (System Core)

### 1.1 启动与生命周期 (Lifecycle & Bootstrap)

- **Bootstrapper 模式**: `core/bootstrap/`
  - 将启动逻辑解耦为独立引导程序，确保依赖注入顺序。
  - **InfrastructureBootstrapper**: 配置、数据库、EventBus。
  - **CoreServicesBootstrapper**: Ticker, SoulManager, Vision, TTS。
  - **BootstrapManager**: 统一编排启动流程。

### 1.2 插件系统 (Plugin System V2)

- **Manifest 驱动**: 基于 `manifest.yaml` (ID, Version, Permissions)。
- **SystemPluginManager**:
  - **Discovery**: 自动扫描，支持 Legacy 插件（自动合成 Manifest）。
  - **Dependency Resolution**: Topological Sort (Kahn's Algo)。
  - **Loader**:
    - **In-Process**: 直接动态导入。
    - **Isolation (`isolation_mode: process`)**: 使用 `RemotePluginProxy` 启动子进程，通过 IPC 桥接 (Queues/Threads) 安全运行组件。

### 1.3 事件总线 (Event Bus)

- **纯异步总线**: 解耦组件通信。
- **Schema Registry**: 强类型定义 (`system.ready`, `plugin.loaded`).

---

## 2. 对话智能 (Chat Intelligence)

### 2.1 统一流水线 (Unified Chat Pipeline)

- **ChatPipeline**: `services/chat/pipeline.py` (Pipes & Filters).
- **Steps**:
  1.  **ContextBuilderStep**: 聚合 Persona + RAG + Dynamic Instruction。
  2.  **ToolPreparationStep**: 注入工具定义。
  3.  **LLMExecutionStep**: 执行 LLM 流生成及 Tool Loop。

### 2.2 上下文与提示词 (Context & Prompt)

- **SoulProvider**: 提供角色设定 (Persona)。
- **PromptManager V1**:
  - Jinja2 模板支持 (`python_backend/prompts/`).
  - 结构化提示词优化 (System, Memory Extract)。

### 2.3 工具系统 (Tooling)

- **Web Search**: `services/chat/tools/search.py` (Brave/DuckDuckGo).

---

## 3. 记忆架构 (Memory Architecture)

### 3.1 驱动工厂 (Driver Factory)

- **MemoryDriverFactory**: `memory/factory.py` (动态加载，Fallback 策略)。

### 3.2 向量与图谱 (SurrealDB V3)

- **Backend**: SurrealDB (Single Source of Truth).
- **Features**:
  - **Hybrid Search**: Vector (HNSW 384d) + FullText.
  - **Knowledge Graph**:
    - 实体消歧 (`_resolve_entity`): 自动合并同义实体。
    - 关系强化 (`add_knowledge_graph`): 自动权重增强。
  - **The Gardener**:
    - 生物衰减 (Time Decay): `strength * 0.99^days`.
    - 周期治理: 每日清除弱连接。

---

## 4. 感知与表达 (Perception & Expression)

### 4.1 音频服务 (Audio Services)

- **Microservices**: `stt_server.py` (SenseVoice), `tts_server.py` (GPT-SoVITS).
- **Performance**:
  - **Lazy Loading**: 主进程不加载模型，仅注册驱动。
  - **Raw Stream Pipe**: GPT-SoVITS -> PCM -> FFmpeg -> AAC Pipe，实现零延迟流式传输 (Zero-latency MSE)。
- **VAD**: 后端集成，前端可视化 (`VoiceInput` 组件)。

### 4.2 视觉与 Live2D (Vision & Frontend)

- **Live2D Backend**:
  - **Emotion Engine**: `emotion_map.json` 映射语言情感到动作。
  - **Motion Triggers**: LLM `[emotion]` 标签驱动。
- **Frontend**:
  - **Auto-Discovery**: 动态端口发现 (`GET /network`)。
  - **Quiet Mode**: 15s 无操作自动进入静默模式，防止打断。

---

## 5. 工程化加固 (Engineering Hardening)

- **构建验证**: `npm run verify-build` (检查资源路径)。
- **类型同步**: `npm run gen-types` (自动生成 TS 定义)。
- **端口同步**: 后端 `GET /network` 接口。
