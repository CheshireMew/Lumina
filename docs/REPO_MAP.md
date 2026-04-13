# Lumina Repository Map

本文档旨在详尽描述 Lumina 项目的目录结构、各文件夹及代码文件的核心作用，作为开发者的导航指南。

---

## 📂 根目录 (Root)

| 文件/目录           | 作用描述                                                                                 |
| :------------------ | :--------------------------------------------------------------------------------------- |
| `app/`              | **Frontend (Electron/React)**。包含 UI 组件、渲染进程逻辑、以及与后端的通信接口。        |
| `python_backend/`   | **Core Backend Service**。项目的灵魂，包含所有业务逻辑、AI 流水线、插件管理和 API 服务。 |
| `archive/`          | **归档区**。存放历史遗留脚本、旧版数据库和不再使用的开发资产。                           |
| `assets/`           | **静态资源**。存放语音样本、图标、以及 UI 音效。                                         |
| `config/`           | **系统配置**。存放 LLM 注册表、服务端口定义等核心配置文件。                              |
| `core/`             | **Electron 服务层**。桥接渲染进程与 Python 后端的逻辑核心（LLM/STT/TTS/Memory）。        |
| `docs/`             | **项目文档**。存放技术规格书 (`TECHNICAL_REFERENCE`)、架构图和开发者指南。               |
| `public/`           | **静态资源**。存放前端使用的图片、字体、以及 Live2D 模型资源。                           |
| `scripts/`          | **自动化脚本**。包含启动脚本、环境验证工具和构建配置文件。                               |
| `mcp_servers/`      | **MCP 卫星服务**。独立的 Model Context Protocol 服务器插件。                             |
| `package.json`      | 工程配置文件，定义 Node.js 依赖、脚本命令及 Electron 构建配置。                          |
| `vite.config.mts`   | Vite 构建配置，定义前端编译选项和别名。                                                  |
| `.gitignore`        | Git 忽略规则，保护敏感配置（如 API Key）和临时文件不被上传。                             |
| `audio_config.json` | STT/TTS 音频配置，包含后端服务端口及录音参数。                                           |

---

## 🎨 资源与配置 (Assets & Config)

### 静态资源 (assets/)

- **`emotion_audio/`**: 情感语音包。根据角色当前情感状态触发的特定短语录音。
- **`icons/`**: 系统图标。用于 UI 界面显示。
- **`sounds/`**: UI 音效。系统启动、消息接收、点击提示等交互音效。

### 系统配置 (config/)

- **`llm_registry.json`**: **LLM 路由注册表**。定义了多个 LLM 供应方（如 Pollinations, OpenAI）并将它们路由到不同的业务功能（对话、记忆摘要、前瞻思考）。
- **`app_config.py` (in backend)**: **主配置逻辑**。统一管理端口、路径和 Pydantic 校验。

---

## ⚙️ 系统服务 (core/)

本目录包含 Electron 主进程使用的领域驱动服务，主要负责复杂业务逻辑的封装及与 Python 后端的 IPC/WebSocket 协调。

- **`backend/`**:
  - **`backend_service.ts`**: Electron 侧后端进程编排入口。负责端口装载、健康检查、拉起和停止核心 Python 进程。
- **`memory/`**:
  - **`memory_service.ts`**: 长期记忆桥梁。负责配置后端记忆接口并提交检索/写入请求。
- **`voice/`**:
  - **`tts_service.ts`**: 语音播放流水线。包含句子切分逻辑及音频缓冲区管理，确保语音输出无缝衔接。

---

## 💻 前端架构 (app/)

### 核心进程

- **`app/main/` (Electron 主进程)**:
  - **`main.ts`**: 程序入口。负责窗口生命周期、受控 IPC 注册、本地协议注册，以及 Python 后端服务启动编排。
  - **`preload.ts`**: 安全网桥。定义了暴露给渲染进程的 API 安全接口。
  - **`config_store.ts`**: 配置持久化。基于 `electron-store` 存储本地桌面偏好。
- **`app/renderer/` (React 渲染进程)**:
  - **`App.tsx`**: UI 根组件。只负责布局和模态层组合，核心业务状态来自统一 Hook。
  - **`core/events.ts`**: 全局事件总线。处理音频 VAD 状态、感知识别结果及 UI 指令的解耦通信。
  - **`hooks/`**: 业务逻辑层。`useCoreSystem` 组合 `useSettings`、`useCharacterState`、`useGateway`、`useAudioPipeline`。
  - **`runtime/gatewayClient.ts`**: WebSocket 单例客户端，统一管理连接、重连和事件分发。
  - **`components/`**: UI 组件库。包含对话框、Live2D 画布及控制面板。

---

## 🎨 前端资产与运行时 (public/)

本目录包含浏览器直接加载的静态资源、低级运行时库以及边缘侧运行的模型文件。

- **`live2d/`**: **Live2D 模型库**。存放所有可选角色的 `.model3.json` 及其纹理资源（如 Hiyori, PinkFox）。
- **`vrm/`**: **3D 模型库**。存放符合 VRM 规格的 3D 角色模型。
- **`libs/`**: **底层运行库**。包含 `live2dcubismcore.min.js` 等闭源 SDK 核心。
- **边缘侧 VAD (Voice Activity Detection)**:
  - **`real-time-vad.js`**: 浏览器端实时语音活性检测逻辑。
  - **`silero_vad_v5.onnx`**: Silero VAD 神经网络模型，用于在前端低功耗识别用户是否正在说话。
  - **`ort-wasm-*.wasm`**: ONNX Runtime 的 WebAssembly 编译产物，为浏览器提供近乎原生的模型推理性能。

---

## 🐍 后端核心 (python_backend/)

Lumina 的后端采用分层架构，集成了 FastAPI 服务、高性能语音微服务以及基于插件的领域驱动设计 (DDD) 逻辑。

### 核心入口 (Entry Points)

- **`main.py`**: **FastAPI 入口**。现在只负责扩展导入路径、初始化日志和调用应用装配工厂。
- **`core/api/app_factory.py`**: **应用装配入口**。统一注册中间件、异常处理、路由、静态资源和 Worker 控制通道。
- **`backend_launcher.py`**: **Worker 启动入口**。负责根据 capability 拉起 `stt` / `tts` / `vision` 等工作进程。

### 架构框架 (core/)

- **`api/`**: **应用装配层**。集中管理 FastAPI app 的装配，不再把中间件和路由细节堆在 `main.py`。
- **`bootstrap/`**: **生命周期引导**。实现基础设施（DB、EventBus）到核心服务的有序依赖注入。
- **`events/`**: **异步事件总线**。提供基于消息驱动的组件通信机制，实现 UI 指令与业务逻辑的解耦。
- **`db/`**: **持久化层**。封装查询构造和数据库抽象，供 PostgreSQL 驱动使用。
- **`interfaces/`**: **契约定义**。包含插件、驱动及服务的抽象基类，确保系统的可扩展性。

### 业务与智能 (services/ & AI)

- **`services/`**:
  - **`container/`**: **依赖注入容器**。中央服务注册表，控制核心组件的实例化与生命周期。
  - **`orchestrators/`**: **领域编排层**。包括角色灵魂和会话管理等高层服务。
  - **`chat/`**: **对话流水线**。`pipeline.py` 负责上下文构建、工具准备和流式执行，`service.py` 提供单轮对话边界。
  - **`process_manager.py`**: **Worker 编排器**。负责托管模式拉起、外部模式挂载和运行状态检查。
  - **`plugin_state_aggregator.py`**: **插件运行态真源**。聚合主进程、Worker 和心跳状态。
- **`llm/`**: **模型驱动层**。屏蔽 OpenAI、DeepSeek、Pollinations 等不同 API 的协议差异。
- **`memory/`**: **记忆系统**。统一通过 PostgreSQL 驱动提供对话日志、向量检索和上下文召回。

### 路由与配置 (routers/ & config)

- **`routers/`**:
  - **`gateway.py`**: WebSocket 中央网关，负责向渲染进程分发实时语音、动画及状态包。
  - **`llm_mgmt.py`**: 运行时模型配置管理，用于动态切换 AI 供应商。
  - **`runtime.py`**: 统一能力运行态视图，向前端暴露 capability 到 runtime 的映射结果。
  - **`vision_routes.py`**: 视觉分析路由，处理图片分析与模型加载。
- **`app_config.py`**: **强类型配置中心**。基于 Pydantic 解析 `.env` 与 `config.yaml`。
- **`logger_setup.py`**: 实现多进程、多服务的日志收集与 RequestID 链路追踪。

---

## 🏗️ 系统插件 (plugins/)

Lumina 拥有强大的插件化生态，分为核心驱动与扩展功能：

- **`drivers/`**: 包含硬件、LLM Provider 及感知模块的具体驱动实现。
- **`extensions/`**: 基于 V2 插件协议的功能扩展（如 MCP 桥接、外部 API 集成）。
- **`system/`**: 系统级插件，如 `voiceprint`（声纹识别）和 `cognitive`（认知层增强）。

---

## 🛠️ 自动化与工具 (scripts/)

- **`start_backend.ps1`**: 一键启动脚本。并发启动 `main`, `stt`, `tts` 服务。
- **`verification/`**: 环境验证脚本。用于测试数据库连接、API 通信及硬件驱动状态。
- **`build_config/`**: 存放 PyInstaller 的 `.spec` 文件，用于打包后端可执行文件。
- **`generate_api_client.ps1`**: 自动化工具。根据 FastAPI 的 OpenAPI schema 自动生成前端 TypeScript 类型。

---

## 📦 存储与数据 (data/)

- **`characters/`**: 角色定义。存放不同角色的 `identity.yaml`, `style.yaml` 和 `state.json`。
- **`sessions/`**: 对话会话。存放用户聊天记录的持久化 JSON。
- **`temp/`**: 运行时临时文件，如临时录音片段。

---

## 📡 插件与扩展

- **`plugins/system/`**:
  - `galgame/`: 游戏逻辑增强（能量系统、好感度）。
  - `cognitive/`: 认知层插件，处理长短期记忆决策。
  - `voiceprint/`: 声纹识别驱动及策略。
- **`mcp_servers/`**:
  - `bilibili/`: 接入 B 站动态与评论。
  - `memory_viewer/`: 记忆系统可视化辅助。

---

> [!TIP]
> 细节说明：所有新增验证脚本请放入 `scripts/verification`；新增角色定义请放入 `python_backend/characters/`。
