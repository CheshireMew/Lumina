# Lumina 项目目标与架构理解

> 生成时间:2026-01-13
> 参考依据:`README.md`、`docs/ARCHITECTURE.md`、`docs/ARCHITECTURE_MCP.md`、代码结构(`python_backend/`、`core/`、`app/`)

## 1. 项目目标(我的理解)

Lumina 是一个"桌面智能伴侣",核心不是单纯聊天,而是"长期陪伴"。目标集中在三件事:

- 沉浸式交互:Live2D 角色 + 语音输入/输出,让对话像在和一个有形象的角色交流。
- 记忆与成长:对话记录、长期记忆与"做梦式整理"是重点,让角色随互动逐步变化。
- 本地优先与隐私:核心能力(STT/LLM/记忆)尽量可本地运行,减少对外部云的依赖。

## 2. 设计原则与总体思路

- 微内核 + 插件扩展:核心稳定、低延迟;扩展能力以 System Plugins 或 MCP 承载。
- 多进程分离:主记忆服务、STT、TTS 各自独立,避免相互阻塞。
- 事件驱动:前后端通过 WebSocket/EventBus 协调"思考-输出"的节奏。

## 3. 总体架构概览(简化图)

```
[Electron/React UI]
    |  HTTP + WebSocket
    v
[FastAPI Memory Server (python_backend/main.py)]
    |-- SurrealMemory -> SurrealDB
    |-- LLMManager -> Provider Drivers (OpenAI/DeepSeek/Pollinations)
    |-- System Plugins (Dreaming/Evolution/Heartbeat/Galgame/Voiceprint)
    |-- MCPHost -> MCP Servers (bilibili, demo_echo, ...)
    |-- Gateway/EventBus -> Cognitive Loop

[STT Server] <----> [TTS Server]
```

## 4. 核心组件说明

### 4.1 前端(Electron + React)

- 负责 UI 与 Live2D 渲染:聊天气泡、Galgame HUD、设置页、插件页等。
- 通过 IPC 与主进程通信,主进程负责启动 Python 后端与端口同步。
- 通过 HTTP/SSE 与 WebSocket 连接后端服务。

### 4.2 主后端(Memory Server)

- 入口:`python_backend/main.py`,负责生命周期与路由挂载。
- 服务容器:`services/container.py` 统一持有 Soul、Memory、LLM、EventBus、PluginManager 等。
- 路由:`routers/` 提供配置、记忆、聊天、调试、插件等 API。

### 4.3 语音服务(STT/TTS)

- STT:`python_backend/stt_server.py`,支持 VAD、驱动式模型切换(SenseVoice/Faster-Whisper 等)。
- TTS:`python_backend/tts_server.py`,通过驱动加载 Edge TTS、GPT-SoVITS、Fish Audio。

### 4.4 记忆系统

- 存储:SurrealDB(WebSocket RPC),表包含 `conversation_log` 与 `episodic_memory`。
- 向量化:Embedding 模型由 `model_manager` 统一管理。
- 检索:向量/全文/混合检索,支持 RAG 注入到对话上下文。

### 4.5 LLM 管理

- `llm/manager.py` 读取 `config/llm_registry.json`,定义 Provider 与 Feature Route。
- 支持多路由:chat/memory/dreaming/evolution/proactive 对应不同模型与参数。

### 4.6 Cognitive Loop 与事件总线

- Gateway 负责前端 WebSocket 事件;CognitiveLoop 负责"输入 -> 推理 -> 输出"流程。
- EventPacket 作为统一消息协议,支持中断与会话管理。

## 5. 关键数据流(用户视角)

### 5.1 文本聊天

1) UI 提交文本 -> `/lumina/chat/completions`
2) ChatService 组装 System Prompt、RAG、历史上下文
3) LLM 生成流式响应 -> SSE 返回前端

### 5.2 语音聊天

1) 前端采集音频 -> STT WebSocket
2) STT 输出文本 -> 进入聊天流程
3) 聊天响应 -> TTS 服务生成音频流 -> 前端播放

### 5.3 记忆写入

- `/memory/add` 将对话写入 SurrealDB;后续由 Dreaming/Evolution 插件整理与演化。

## 6. 扩展体系

- System Plugins:`python_backend/plugins/system/`,可加载独立功能(如 Dreaming、Heartbeat)。
- Driver Plugins:`python_backend/plugins/drivers/`,用于替换 STT/TTS/LLM 引擎。
- MCP Servers:`python_backend/mcp_servers/`,独立进程提供外部工具能力。

## 7. 配置与运行要点

- 端口:`config/ports.json` 统一配置 memory/stt/tts/surreal 端口。
- 数据目录:优先 `Lumina_Data` 或 `LUMINA_DATA_PATH`,否则使用系统 AppData。
- 启动方式:推荐 `start_lumina.ps1`,或分别启动 SurrealDB + Python 后端 + 前端。

## 8. 当前演进方向(从文档与代码推断)

- 插件权限与热加载、沙箱隔离(MCP/Plugin 安全)。
- 更完整的 RAG/记忆整理流程与后台摘要任务。
- 多角色与跨平台支持。

---

如果需要更深层的细节,请继续阅读:
- `docs/ARCHITECTURE.md`
- `docs/ARCHITECTURE_MCP.md`
- `docs/LUMINA_MEMORY_ARCHITECTURE_V2.md`
