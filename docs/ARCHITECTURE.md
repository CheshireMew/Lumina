# Lumina 系统架构文档 (v2026.1)

> 最后更新: 2026-01-18
> 状态: 稳定 / 混合微服务架构 (Hybrid-Microservice)

本文档详细描述了 Lumina 项目当前的架构设计，重点涵盖 **混合进程模型 (Hybrid Process Model)**、**插件系统 2.0** 以及 **记忆架构**。

---

## 1. 宏观概览 (High-Level Overview)

Lumina 是一个**本地优先 (Local-First)**、**以隐私为中心**的 AI 桌面伴侣。它采用了一种**混合架构**，结合了以下组件：

1.  **Electron (前端)**: 负责用户界面、Live2D 渲染、操作系统集成。
2.  **FastAPI (主后端)**: 负责核心编排、记忆管理、插件系统、LLM 逻辑。
3.  **Worker Services (微服务子进程)**: 负责 CPU/GPU 密集型任务（如 STT 语音转文字、TTS 语音合成），运行在独立进程中以避免阻塞主线程。
4.  **SurrealDB**: 嵌入式/服务器模式数据库，提供图数据库 (Graph) 和向量数据库 (Vector) 能力。

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
        MainBackend -->|查询/写入| DB[(SurrealDB)]
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

## 3. 插件系统 2.0 (Plugin System)

新的插件架构强调 **安全性**、**热重载** 和 **远程能力**。

### 3.1 插件清单 (`manifest.yaml`)

每个插件（无论是逻辑、驱动还是 UI 组件）都由清单文件定义：

```yaml
id: system.voiceprint
version: 1.0.0
category: driver # stt, tts, skill, system, driver
group_id: stt # 用于 UI 分组 (如 SenseVoice 属于 STT 组)
runtime_target: main # 'main' (在主进程运行) 或 'stt_server' (在远程进程运行)
permissions: # 安全策略
  - file_system_read
```

### 3.2 加载机制

1.  **发现 (Discovery)**: 扫描 `plugins/system/` 和 `plugins/extensions/` 目录。
2.  **清单解析**: 读取 YAML 并确定 `runtime_target`。
    - **Main Target**: 将 Python 类加载到主进程中。
    - **Remote Target**: 在主进程中创建一个 `RemotePluginStub`（远程插件桩）。实际代码在 Worker 进程中运行。
3.  **沙箱化 (Sandboxing)**:
    - 带有 `permissions` 的插件会获得 `SandboxedContext`（受限 API）。
    - 受信任的系统插件获得标准的 `LuminaContext`。

### 3.3 热重载 (Hot Reload)

- **启用/禁用**: 支持运行时动态切换。
- **重载**: 支持卸载 Python 模块并重新导入（实验性功能）。
- **配置**: 通过 UI 中的 `config_schema` 进行动态配置。

---

## 4. 记忆架构 (SurrealDB)

利用 SurrealDB 的多模态能力（图 + 文档 + 向量）。

### 4.1 记忆层级

1.  **短期记忆**: RAM / 上下文窗口 (Context Window)，保留最近 N 轮对话。
2.  **中期记忆**: `conversation_log` 表 (保留近期历史，支持向量检索)。
3.  **长期记忆**: `knowledge_graph` (实体-关系图谱)。

### 4.2 安全性

- **基于角色的访问控制 (RBAC)**: 应用以 `app_user` (Owner 角色) 身份连接，确保在其命名空间内拥有完全控制权。
- **权限自愈**: `SurrealDriver` 在连接时会自动检查并修复受损的权限配置。

---

## 5. 前端架构 (React)

### 5.1 状态与配置

- **PluginStoreModal**: 统一的插件市场，涵盖技能 (Skills)、驱动 (STT/TTS) 和系统模块。
- **SWR 缓存**: 采用 "Stale-While-Revalidate" 策略，实现 UI **秒开**体验。
- **VoiceprintConfigPanel**: 专门的生物识别管理面板。

### 5.2 通信

- **REST API**: 用于配置管理、插件开关。
- **WebSocket**: 用于实时聊天流、音频流传输、状态推送。

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
