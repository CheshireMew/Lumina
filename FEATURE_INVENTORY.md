# 功能清单 (Feature Inventory)

> Last Updated: 2026-01-20 (Post-Audit Refactor)

## 1. 核心架构 (System Core)

### 1.1 启动与生命周期 (Lifecycle & Bootstrap)

- **Bootstrapper 模式**: `core/bootstrap/`
  - 将启动逻辑解耦为独立引导程序，确保依赖注入顺序。
  - **InfrastructureBootstrapper**: 配置、数据库、EventBus (LifecycleBus)。
  - **CoreServicesBootstrapper**: Ticker, SoulService, Vision, TTS。
  - **BootstrapManager**: 统一编排启动流程。

### 1.2 插件系统 (Plugin System V3)

- **Hybrid Architecture (混合架构)**:
  - **Main Process**: `SystemPluginManager` (SSOT) 管理所有插件状态，负责 `Extension` 和 `Native` 插件。
  - **Worker Processes**: `STT/TTS` Server 通过独立的 `PluginLoader` 加载驱动，通过 JSON-RPC/HTTP 接受 Main 进程指令。
- **Manifest 驱动**: 基于 `manifest.yaml` (ID, Version, Permissions, Runtime Target)。
- **核心组件**:
  - **Security Policy**: 严格的权限检查 (SandboxedContext) 和隔离策略。
  - **Discovery**: 自动扫描 `plugins/system` 和 `plugins/extensions`。
  - **Hot Reload (热重载)**: ✅ 已实现，无需重启后端即可更新插件代码。
- **API Version**: `@api_stable("1.0")`, `@api_experimental`, `@deprecated()` 装饰器标记 API 稳定性。
- **Performance Monitor**: 自动监控插件初始化时间和事件处理耗时，超时告警。
- **CLI Generator**: `python scripts/create_plugin.py my_plugin` 快速创建插件模板。

#### Plugin API Endpoints

| Endpoint                 | Method | Description                             |
| ------------------------ | ------ | --------------------------------------- |
| `/plugins/list`          | GET    | 列出所有插件状态                        |
| `/plugins/toggle`        | POST   | 启用/禁用插件                           |
| `/plugins/reload/{id}`   | POST   | **热重载插件** (清除模块缓存并重新加载) |
| `/plugins/config/plugin` | POST   | 更新插件配置                            |
| `/plugins/upload`        | POST   | 上传 .zip 插件包并自动安装              |
| `/plugins/slots`         | GET    | 获取插件 UI 组件                        |

- **State Sync**:
  - `LifecycleBus` (Postgres) 作为分布式状态源 (SSOT)。
  - **Adaptive Polling**: Worker 进程自适应轮询配置变更。

#### [NEW] Plugin State Aggregator (Architecture 7.0)

事件驱动的集中式状态聚合器，替代分散的状态合并逻辑：

```
数据源 → 发事件 → Aggregator 监听 → 更新缓存
list_all_plugins() → 读缓存 → 返回 (O(1))
```

- **Event Sources**: `plugin.state.local`, `plugin.state.worker`, `plugin.state.mcp`, `plugin.state.ticker`
- **Unified Status Computation**: `_compute_status()` 集中处理 desired_enabled + active_status
- **Offline Detection**: 30秒超时自动标记为 `offline`

### 1.2 错误处理 (Error Handling)

- **Exception Hierarchy**: `core/exceptions.py` - 统一异常层次 (PluginError, ServiceError, etc.)。
- **Error Monitor**: `services/error_monitor.py` - 错误追踪、spike 检测、统计。
- **Debug Endpoints**: `/admin/debug/errors`, `/admin/debug/system` 查看系统状态。

### 1.3 事件总线 (Event Bus)

- **Memory Bus**: 进程内高性能通信 (`core.events`).
- **LifecycleBus**: 基于 Postgres 的分布式状态同步。
- **Monitoring**: `bus.get_stats()`, `bus.check_for_leaks()` 订阅泄漏检测。
- **HTTP Pool**: 共享 httpx 客户端池 (`http_client.py`)，避免每请求创建连接。

---

## 2. 对话智能 (Chat Intelligence)

### 2.1 极简流水线 (Refactored Chat Service)

- **ChatService**: `services/chat_service.py`
  - **职责单一**: 仅负责对话流控制 (Stream Orchestration)。
  - **Memory-Driven**: 不再手动管理向量，直接调用 `MemoryService.retrieve_context()`。
  - **Tool-Agnostic**: 工具执行逻辑解耦至 `LLMManager`。

### 2.2 上下文与提示词 (Context & Prompt)

- **SoulService**:
  - 动态 Prompt 组装: `System Template` + `Character Config` + `Driver Hooks`。
  - **Persona Engine**: 支持多角色切换 (`characters/` 目录)。
- **LLMManager**:
  - **Route System**: 基于功能的路由 (Chat, Memory, Dreaming)，支持动态切换模型提供商。
  - **Dynamic Injection**: 插件可注册新的 Route。

---

## 3. 记忆架构 (Memory Architecture)

### 3.1 抽象服务层 (Memory Service)

- **Service Facade**: `MemoryService` (原 `SurrealMemory`)。
- **High-Level API**: `retrieve_context(text)` 封装了 Embedding 生成和混合检索逻辑。
- **Driver Layer**: 支持 SurrealDB 和 Postgres (PgVector) 驱动。

### 3.2 向量与知识 (Knowledge Engine)

- **LTM (Long-Term Memory)**: Postgres + pgvector 向量相似性检索 (替换 SurrealDB)。
- **Embedding Cache**: LRU 缓存避免重复向量计算 (`embedding_cache.py`)。
- **Knowledge Graph**: 实体关系网络 (Entity-Relation)。
- **Automatic Optimization**:
  - **The Gardener**: 后台任务，定期清理微弱连接，合并重复实体。

---

## 4. 感知与表达 (Perception & Expression)

### 4.1 音频流水线 (Audio Transducer)

- **STT Server**: 纯净转录器 (Pure Transducer)。
  - **移除耦合**: 声纹验证 (Voiceprint) 逻辑已移除，不再阻塞转录流。
  - **Fast Path**: 音频数据直接流向 `SenseVoiceSmall` 模型。
- **TTS Manager**:
  - **Plugin-Driven**: 支持 `EdgeTTS` 等多种驱动动态切换。
  - **Worker Isolation**: 运行在独立子进程，避免阻塞主线程。

### 4.2 视觉与交互 (Vision & Interaction)

- **VisionService**:
  - **Screen Capture**: `mss` 高效截屏。
  - **Multimodal LLM**: 集成 `Moondream` 或 `GPT-4o` 视觉能力。
- **Frontend IPC**:
  - **Sandboxed Bridge**: Electron ContextIsolation 启用。
  - **Dynamic Port (API)**: 前端通过 `GET /network` 获取后端端口 (Architecture 7.0)。
  - **Removed**: `connection.json` 文件写入已移除，改用 API 发现。

---

## 5. 工程化加固 (Engineering Hardening)

- **Security**:
  - **SecretManager**: 实现优先级密钥加载 (Env > Keyring > Config)，解耦敏感信息与明文配置。
  - **Token Authentication**: JWT 驱动的插件权限验证。
  - **Sandbox**: 启用 Electron 沙箱及 contextIsolation。
- **Testing**:
  - **Pytest Ecosystem**: 统一测试目录 `automation/tests/`.
  - **CI/CD Pipeline**: 集成 GitHub Actions (ci.yml) 进行自动化验证。
  - **Performance Benchmarks**: ✅ 已建立，基于 `pytest-benchmark` 的微基准与压力测试。
  - **Frontend Unit Tests**: ✅ 已建立，基于 `Vitest` 的 React 组件单元测试环境。
  - **Chaos Testing**: ✅ 已实现，包含模拟网络延迟、资源耗尽及服务故障注入。
- **Linting**: 严格的各类 Check (Type, Import)。
- **Repo Map**: 自动化生成的代码库导航图。
