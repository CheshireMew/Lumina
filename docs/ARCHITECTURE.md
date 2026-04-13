# Lumina 系统架构文档 (v2026.4)

> 最后更新: 2026-04-10
> 状态: 稳定 / 微内核主进程 + Worker 能力进程

本文档描述 Lumina 当前真实生效的运行底座，重点是 **统一插件内核**、**主进程/Worker 分工** 和 **记忆架构**。

---

## 1. 宏观概览 (High-Level Overview)

Lumina 是一个**本地优先 (Local-First)**、**以隐私为中心**的 AI 桌面伴侣。它采用了一种**混合架构**，结合了以下组件：

1.  **Electron (前端)**: 负责用户界面、Live2D 渲染、操作系统集成。
2.  **FastAPI (主后端)**: 负责核心编排、记忆管理、插件系统、LLM 逻辑。
3.  **Worker Services (微服务子进程)**: 负责 CPU/GPU 密集型任务（如 STT 语音转文字、TTS 语音合成），运行在独立进程中以避免阻塞主线程。
4.  **PostgreSQL + pgvector**: 统一承载结构化数据、向量检索和生命周期状态。

```mermaid
graph TD
    User[用户] -->|交互| Frontend[Electron 应用]
    Frontend -->|HTTP/WebSocket| MainBackend[Python 主进程 (FastAPI)]

    subgraph "Python 后端集群"
        MainBackend -->|任务分发| STT[STT 服务器 (Worker)]
        MainBackend -->|任务分发| TTS[TTS 服务器 (Worker)]
        MainBackend -->|管理| Plugins[系统插件]
    end

    subgraph "数据层"
        MainBackend -->|查询/写入| DB[(PostgreSQL + pgvector)]
        MainBackend -->|文件读写| FS[文件系统]
    end
```

---

## 2. 混合进程模型 (Hybrid-Hybrid)

我们采用独特的 **混合双模启动模型 (Hybrid-Hybrid Startup Model)**，以最大限度地为开发者提供灵活性，同时为用户提供稳定性。

### 2.1 运行模式

1.  **托管模式 (Managed Mode)** (默认): `ProcessManager` 会自动启动并管理 STT/TTS 子进程。如果进程崩溃，它会尝试重启。
2.  **外部模式 (External Mode)** (开发专用): 开发者可以手动运行 `backend_launcher.py stt`。主进程的 `ProcessManager` 会检测到端口已被占用，从而**自动挂载**到这个外部进程，而不是尝试启动新进程。

### 2.2 优势

- **可调试性 (Debuggability)**: 你可以随时停止 STT 服务，修改代码，然后手动重启它，而无需重启整个后端。
- **弹性 (Resilience)**: 在托管模式下，进程崩溃可自动恢复。
- **性能 (Performance)**: 将繁重的 PyTorch 模型（Whisper/ChatTTS）与主逻辑循环隔离，互不影响。

---

## 3. 统一插件内核 (Plugin Kernel)

插件系统现在只有一套 contract，不再同时维护旧插件基类和 SDK 基类。

### 3.1 稳定 Manifest

每个插件目录只保留一个 `manifest.yaml`，稳定字段固定为：

```yaml
id: system.emotion_broker
api_version: "1.0"
kind: processor
capability: chat.post_processor
runtime_target: main
permissions:
  - eventbus.subscribe
  - eventbus.emit
config_schema: {}
provides:
  - avatar
```

### 3.2 唯一生命周期

所有正式插件统一实现以下方法：

1. `load(context)`
2. `enable()`
3. `disable()`
4. `unload()`
5. `health()`
6. `get_metadata()`

插件上下文只暴露事件、能力发现、插件配置、插件数据和路由注册，不允许直接碰容器内部对象。

### 3.3 内核只保留六类职责

1. 配置
2. 权限
3. 安全
4. 进程管理
5. 能力注册表
6. 统一网关

### 3.4 能力注册表

系统现在只认 capability，不认具体实现类。主进程和 Worker 汇报都会收敛到同一套能力标识，例如：

- `stt`
- `tts`
- `llm`
- `memory`
- `avatar`
- `tool.search`
- `chat.context`
- `chat.post_processor`

### 3.5 配置与状态

- 所有启停意图和当前 provider 只从 `config.plugins` 读取。
- `desired_state` 可写，是唯一用户意图真源。
- `runtime state` 只读，由 `plugin_state_aggregator` 汇总。
- 前端插件列表只看聚合后的运行态视图，不再各模块各算一份状态。

---

## 4. 记忆架构 (PostgreSQL)

当前记忆层统一建立在 PostgreSQL + pgvector 之上。

### 4.1 记忆层级

1.  **短期记忆**: RAM / 上下文窗口 (Context Window)，保留最近 N 轮对话。
2.  **中期记忆**: `conversation_log` 表 (保留近期历史，支持向量检索)。
3.  **长期记忆**: `knowledge_graph` (实体-关系图谱)。

### 4.2 安全性

- **数据库账号隔离**: 后端统一通过 `memory.postgres` 配置连接 PostgreSQL。
- **降级启动**: 数据库不可用时主进程仍可启动，记忆能力退化为不可用而不是整机崩溃。

---

## 5. 前端架构 (React)

### 5.1 状态与配置

- **`useCoreSystem`**: 前端唯一应用编排入口，统一组合角色、设置、聊天流和音频流水线。
- **`useSettings`**: 本地桌面偏好与运行时 LLM 配置的唯一写入口。设置弹窗只编辑草稿，不直接触碰存储。
- **`useCharacterState`**: 角色列表、当前角色和持久化切换的单一边界。
- **`runtime/gatewayClient.ts`**: WebSocket 单例客户端，统一负责连接、重连、会话号和事件分发。
- **`PluginStoreModal` / `VoiceprintConfigPanel`**: 插件与声纹配置 UI，消费后端聚合态，不再各自计算运行状态。

### 5.2 通信

- **Electron IPC**: 只暴露受控的 `settings`、`app`、`stt` 接口给渲染进程。
- **REST API**: 用于配置管理、角色管理、插件控制和能力查询。
- **WebSocket**: 通过统一网关传输聊天流、情绪、Widget 和插件状态事件。

---

## 6. 目录结构

```
Lumina/
├── app/                    # Electron + React 前端
│   ├── main/              # 主进程 (安全, 窗口管理)
│   └── renderer/          # UI 渲染逻辑
├── python_backend/         # 核心逻辑后端
│   ├── services/          # 服务层 (Plugin, Process, Audio)
│   ├── plugins/           # 插件目录
│   │   ├── system/        # 核心逻辑插件
│   │   └── extensions/    # 硬件驱动 (STT/TTS/VAD)
│   ├── core/              # 抽象基类 & 接口定义
│   └── main.py            # 入口文件
└── docs/                   # 项目文档
```
