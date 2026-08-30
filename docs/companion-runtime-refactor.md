# Lumina Companion Runtime 重构指导

本文档是 Lumina 后续架构重构的执行边界。它不是讨论稿，也不是兼容计划。

目标很明确：把 Lumina 收束成一个本地优先、单角色、Live2D 形象驱动的 AI 伴侣。所有不服务这个目标的架构都应删除；所有已经被替代的旧边界都应一次性迁移并移除，不保留兼容层。

## 1. 产品边界

### 必须保留

- 单角色伴侣体验，默认 Hiyori。
- Live2D 形象、表情、动作、口型联动。
- 文本对话和语音对话。
- VAD、STT、声纹识别、TTS。
- Vision 图像和屏幕理解。
- 长期记忆、会话上下文、用户画像。
- 轻量主动性，用于陪伴、提醒和自然互动。
- 内部 provider/capability 机制，用于装配 LLM、STT、TTS、Vision、Search、Memory、Voiceprint。
- Worker 进程隔离，用于承载重能力，不用于承载产品状态。

### 必须删除

- 对外插件平台语义。
- 插件商店、插件上传、marketplace、插件 UI slot、动态插件路由。
- 多角色、角色市场、角色切换器。
- VRM、Sprite 或其它非 Live2D 形象运行时。
- GalGame HUD、剧情章节、好感度、能量值、关系等级、Lv、进度条、雷达图、PAD 数值面板。
- Bilibili、弹幕、直播互动。
- 旧审计、旧迁移、旧实验报告、旧恢复逻辑。
- 任何为了“旧调用还能跑”而保留的 adapter、alias、shim、legacy helper、旧类型、旧导出。

### 明确判断

Live2D 不是可选装饰，也不是待删除插件。它是 AI 伴侣的第一视觉界面。

要删除的是平台化插件架构，不是内部能力装配；要删除的是多形象运行时，不是 Live2D；要删除的是游戏化数值，不是情绪、动作和口型反馈。

## 2. 目标架构

```text
Electron Shell
  - 窗口生命周期
  - 本地文件协议
  - 后端启动和停止
  - 本地设置桥接

React Companion UI
  - Live2D Avatar Layer
  - Conversation Dock
  - Voice Input
  - Settings Workspace
  - Runtime Status

Python Companion Runtime
  - CompanionRuntime
  - ChatTurnService
  - CompanionContext
  - Soul
  - Session
  - Memory
  - Emotion
  - Proactive
  - Tool planning

Capability Layer
  - LLM Provider
  - STT Provider
  - TTS Provider
  - Vision Provider
  - Search Provider
  - Memory Provider
  - Voiceprint Provider

Worker Runtime
  - STT worker
  - TTS worker
  - Vision worker

Local SQLite (default) / PostgreSQL + pgvector (optional)
  - session history
  - conversation log
  - episodic memory
  - profile memory
  - runtime state
```

## 3. 架构铁律

### 单一来源

- 所有对话回合只允许从 `ChatTurnService` 进入。
- 所有用户、角色、会话身份只允许从 `CompanionContext` 解析。
- 所有后端伴侣行为只允许由 `CompanionRuntime` 编排。
- 所有长期记忆读写只允许通过 `MemoryService`。
- 所有短期会话历史只允许通过 `SessionManager`。
- 所有前后端实时消息只允许使用 gateway websocket 和 `EventPacket`。
- 所有能力选择只允许通过 capability/provider 配置。

### 禁止事项

- 禁止新增第二套 chat/completions 对话入口。
- 禁止 router 直接拼接 soul、memory、session、llm 的业务流程。
- 禁止前端保存真实会话历史作为后端历史来源。
- 禁止 worker 修改 companion state。
- 禁止 provider 拥有产品业务状态。
- 禁止用“兼容旧插件”作为理由保留 plugin 命名。
- 禁止迁移一半后同时保留 plugin 和 provider 两套概念。

## 4. 目标目录

推荐最终目录：

```text
app/
  main/
    main.ts
    preload.ts
    config_store.ts
    safe_fs.ts
  renderer/
    companion/
      CompanionScreen.tsx
      runtime/
        companionClient.ts
        CompanionRuntimeProvider.tsx
      avatar/
        AvatarLayer.tsx
        live2d/
      conversation/
        ConversationDock.tsx
        MessageStream.tsx
      voice/
        VoiceController.tsx
      settings/
        SettingsWorkspace.tsx
    runtime/
      gatewayClient.ts
      events.ts

python_backend/
  core/
    events/
    protocols/
    runtime/
    db/
    api/
  services/
    companion/
      runtime.py
      context.py
      interaction.py
      emotion.py
      proactive.py
    chat/
      service.py
      pipeline.py
      providers.py
    memory/
    providers/
    workers/
  capabilities/
    llm/
    stt/
    tts/
    vision/
    search/
    voiceprint/
  routers/
    gateway.py
    companion.py
    settings.py
    capabilities.py
    memory.py
    runtime.py
    debug.py
```

最终状态中不应再有 `python_backend/plugins` 作为主架构目录。如果迁移过程需要临时保留，必须在同一阶段结束时删除。

## 5. 后端重构目标

### CompanionRuntime

新增或收束：

```text
python_backend/services/companion/runtime.py
```

职责：

- 接收用户输入、语音转写输入、主动触发输入。
- 创建 `CompanionContext`。
- 调用 `ChatTurnService`。
- 处理中断、会话重置、状态查询。
- 统一触发交互后副作用：session history、memory log、soul activity、emotion。
- 向 gateway 输出伴侣事件。

`CompanionRuntime` 不负责具体 LLM 请求、不直接写数据库、不直接加载模型。

### ChatTurnService

保留为唯一回合入口。

职责：

- 构建本轮消息。
- 调用 `ChatPipeline`。
- 流式输出 token。
- 调用 `CompanionInteractionRecorder` 落盘。

禁止其它服务绕过它直接调用 `ChatPipeline` 形成新入口。

### ChatPipeline

职责收缩为：

- 接收 `CompanionContextPack`。
- 构建 system prompt。
- 准备 tools。
- 调用 LLM driver。
- 执行有限 tool loop。

它不应直接决定用户身份、角色身份、session 归属。

### CompanionContextPack

新增上下文构建边界：

```text
CompanionContextPack
  identity
  recent_session_history
  relevant_memories
  stable_profile_facts
  current_soul_state
  runtime_capabilities
  current_time
```

Chat pipeline 只吃这个 pack，不到处自己查 memory/soul/session。

## 6. 能力系统重构

### 命名迁移

旧命名必须整体替换：

```text
SystemPluginManager       -> ProviderManager
PluginService             -> ProviderConfigService
PluginManifest            -> ProviderManifest
PluginContext             -> ProviderContext
PluginPermission          -> 删除，除非确实仍有内部 provider 权限需求
plugins.desired_state     -> capabilities.desired_state 或删除
plugins.selected_providers -> capabilities.selected_providers
plugins.settings          -> capabilities.settings
plugin_state_sync         -> capability_state_sync 或删除
/plugins/*                -> /capabilities/* 或具体能力路由
```

迁移完成后，代码库不应再存在对外插件平台语义。

允许存在的概念：

- provider
- capability
- driver
- runtime package
- worker

不允许存在的概念：

- marketplace
- plugin upload
- plugin slot
- third-party plugin lifecycle
- public plugin sandbox
- dynamic plugin UI route

### Provider 边界

Provider 只负责能力实现：

- LLM provider 返回 LLM driver。
- STT provider 执行语音识别。
- TTS provider 执行语音合成。
- Vision provider 执行图像理解。
- Search provider 执行搜索。
- Memory provider 执行 memory driver。
- Voiceprint provider 执行声纹识别。

Provider 不保存会话历史，不保存伴侣状态，不直接写 soul，不决定 UI。

## 7. Router 收口

目标路由：

```text
/lumina/gateway/ws
/companion/message
/companion/interrupt
/companion/session/reset
/companion/state
/settings/*
/capabilities/*
/memory/*
/runtime/health
/runtime/packages/*
/debug/* 仅开发模式
```

迁移规则：

- `/completions/*` 不再作为产品入口，统一迁到 `/companion/message` 或内部 service。
- `/llm-mgmt/*` 迁到 `/settings/llm/*` 或 `/capabilities/llm/*`。
- `/plugins/voiceprint/*` 迁到 `/capabilities/voiceprint/*`。
- `/admin/*` 只允许开发模式或删除。
- `debug` 路由不能成为产品功能依赖。

完成后删除旧 router 文件、旧 schema、旧 generated type。

## 8. 前端重构目标

### UI 分层

`App.tsx` 只保留顶层组合：

```text
CompanionScreen
  AvatarLayer
  ConversationDock
  VoiceController
  AppToolbar
  ModalLayer / SettingsWorkspace
```

`useCoreSystem` 不再继续膨胀。它应迁移为：

```text
companion/runtime/CompanionRuntimeProvider.tsx
companion/runtime/companionClient.ts
```

### Live2D

Live2D 保留为第一等 UI 能力。

职责：

- 加载 Hiyori Live2D model。
- 响应 emotion event。
- 响应 speech/audio event 做口型联动。
- 响应 motion event。
- 在能力降级时仍保持可见。

Live2D 不应知道 LLM、memory、session、provider 配置。

### 前端状态

Zustand 只保存 UI 临时态：

- websocket 是否连接。
- 当前是否 streaming。
- 当前屏幕消息。
- 当前 emotion。
- 当前 UI mode。
- 当前 session id 的显示值。

真实会话历史以后端 `SessionManager` 为准。

禁止前端把本地 `messages` 当作后端上下文来源。

## 9. 记忆系统重构

记忆必须从普通 RAG 升级为伴侣核心能力。

目标分层：

```text
session_history
  当前会话短期上下文。

conversation_turns
  原始交互流水。只追加，只记录发生过什么，不直接代表长期记忆。

memory_items
  唯一长期记忆真源。用 memory_type 区分 episode、fact、preference、profile、relationship、instruction。

memory_consolidation_jobs
  后台提炼任务状态。负责把 turn 中真正重要的信息沉淀为 memory_items。
```

读取规则：

- chat 不直接读多张表。
- memory 不替 AI 决策，只提供长期事实。
- 由 `MemoryService` 构建长期事实上下文，`CompanionContextPackBuilder` 只消费结果。

写入规则：

- 每轮对话先写 session history。
- 原始对话写 conversation_turns。
- 后台或轻量任务提炼 memory_items。
- 记忆写入失败默认不打断对话，但初始化阶段 memory backend 不可用可以阻断启动。

## 10. Worker 重构目标

Worker 只承载重能力：

- STT
- TTS
- Vision

Worker 可以拥有 provider manager，但只用于加载本 worker 的 provider。

Worker 禁止：

- 保存 session history。
- 修改 soul。
- 修改 memory 语义。
- 直接给前端发产品事件。
- 参与 companion decision。

主进程通过 worker control 管理 worker 生命周期、健康状态、配置同步。

如果某个 worker 能力不可用，系统应降级：

- STT 不可用：文本对话仍可用。
- TTS 不可用：文本和 Live2D 仍可用。
- Vision 不可用：对话和记忆仍可用。
- Live2D 资源不可用：允许显示最小 fallback，但这是 UI 降级，不是删除 Live2D。

## 11. 配置重构

目标配置结构：

```yaml
companion:
  character_id: hiyori
  user_id: default_user
  user_name: Master

capabilities:
  selected_providers:
    memory: driver.memory.sqlite
    llm.chat: driver.llm.pollinations
    stt: driver.stt.sensevoice
    tts: driver.tts.edge
    vision: driver.vision.moondream
    tool.search: driver.tool.search.brave
  settings:
    driver.llm.openai: {}
    driver.tool.search.brave: {}

runtime:
  network:
    host: 127.0.0.1
    core_port: 8010
    stt_port: 8765
    tts_port: 8766

memory:
  sqlite_file: database/lumina.sqlite3
  postgres: {}
  history_limit: 20
  overflow_strategy: slide
```

删除：

- `plugins.*`
- 多角色配置入口。
- 旧 memory config 文件。
- 双写到不同配置文件的恢复逻辑。

迁移时允许写一次性迁移脚本，但迁移脚本不能变成运行时兼容层。

## 12. 迁移阶段

### 阶段 1：锁定主入口

目标：

- 所有文本输入、语音输入、主动触发都进入 `ChatTurnService`。
- `ChatTurnEventAdapter` 只做 transport adapter。
- 新增 `CompanionRuntime` 包住现有 chat/soul/session/memory。

删除：

- 其它直接调用 `ChatPipeline` 的产品入口。
- 旧 completions 产品入口。

验收：

- 搜索产品路径中只有 `ChatTurnService` 调用 `ChatPipeline.run`。
- 文本和语音共用同一回合记录逻辑。

### 阶段 2：前端 thin client

目标：

- 新建 `CompanionRuntimeProvider`。
- `App.tsx` 只组合 UI。
- `useCoreSystem` 拆分或删除。
- `useChatStore.messages` 不再作为后端上下文来源。

删除：

- 前端对后端内部服务概念的直接编排。
- 前端重复 session reset 逻辑。

验收：

- 前端只发送 companion event。
- 真实历史刷新后仍可从后端恢复。

### 阶段 3：plugin 到 provider 一次性迁移

目标：

- `plugins` 目录、配置、manager、manifest、routes 全部迁移成 provider/capability。
- 内部能力仍可动态选择。
- 不再存在对外插件平台概念。

删除：

- `SystemPluginManager`
- `PluginService`
- `PluginManifest`
- `PluginContext`
- `PermissionChecker`
- `sandboxed_context`
- `/plugins/*`
- marketplace/upload/slot 相关残留

验收：

- `rg "plugin|Plugin|plugins"` 只允许命中第三方库注释、历史文档删除记录或明确必要的构建工具残留；产品代码不应使用 plugin 作为架构概念。
- 配置文件中没有 `plugins:`。
- API schema 中没有 `/plugins/`。

### 阶段 4：router 收口

目标：

- 路由收束成 companion/settings/capabilities/memory/runtime/debug。
- debug/admin 不参与产品流程。

删除：

- 重复 router。
- 旧 schema。
- 旧 generated type。

验收：

- OpenAPI 中无旧路由。
- 前端 API client 无旧路由类型。

### 阶段 5：记忆升级

目标：

- 建立 `CompanionContextPackBuilder`。
- session、conversation_turns、memory_items、memory_consolidation_jobs 分层。
- prompt 只读 context pack。

删除：

- chat pipeline 内部零散 memory 查询。
- router 直接 SQL 查询作为产品能力。
- 旧 RAG 拼接 helper。

验收：

- chat prompt 的动态上下文来源单一。
- 记忆失败有明确降级策略。

### 阶段 6：清理旧架构

目标：

- 删除所有旧目录、旧类型、旧 helper、旧导出、旧恢复逻辑。
- 更新测试命名。
- 更新 README 和构建脚本。

验收：

- `npm run lint` 通过。
- `npx tsc --noEmit` 通过。
- `python -m compileall -q python_backend` 通过。
- 关键后端测试通过。
- 搜索不到旧架构入口。

## 13. 删除清单

以下项目在迁移完成后必须不存在：

```text
python_backend/plugins/
python_backend/services/plugin_service.py
python_backend/services/system_plugin_manager.py
python_backend/services/plugin_state_sync.py
python_backend/services/plugin_state_aggregator.py
python_backend/services/plugin_kernel/
python_backend/core/api/sandboxed_context.py
python_backend/core/permissions.py
routers 中的 /plugins 路由
config 中的 plugins 配置段
前端 api-schema 中的 /plugins 路径
任何 marketplace/upload/slot 动态 UI 入口
```

如果某个文件中仍有可复用能力，迁移到 provider/capability 后删除原文件。

不要留下空壳文件，不要留下 re-export，不要留下 deprecated alias。

## 14. 测试策略

重构不是纯重命名，测试要跟着边界改。

保留并改名：

- chat turn tests
- companion context tests
- session manager tests
- memory router/service tests
- worker runtime tests
- provider selection tests
- capability package tests

删除或重写：

- plugin lifecycle tests
- plugin sync tests
- plugin isolation tests
- plugin context tests
- marketplace/upload/slot tests

新增：

- `CompanionRuntime` text turn test。
- `CompanionRuntime` interrupt test。
- `CompanionRuntime` session reset test。
- `CompanionContextPackBuilder` memory selection test。
- provider selection test。
- Live2D asset availability fallback test。

## 15. 最终验收

架构验收必须同时满足：

- Live2D 是默认主界面体验。
- 文本对话在无 STT/TTS/Vision 时仍可运行。
- 语音对话使用同一套 companion turn。
- 所有真实会话历史来自后端。
- 所有长期记忆通过 `MemoryService`。
- 所有 prompt 动态上下文来自 `CompanionContextPack`。
- 所有 provider 通过 capability 系统选择。
- worker 不拥有产品状态。
- OpenAPI 无 `/plugins/*`。
- 配置无 `plugins:`。
- 产品代码无对外插件平台语义。
- 旧架构文件已经删除，而不是被闲置。

## 16. 执行原则

每一阶段都按根因收口，不按现象打补丁。

如果发现两个边界都能做同一件事，先确定唯一边界，再迁移所有调用点，最后删除旧边界。

如果一个旧模块只剩“兼容旧路径”的作用，直接删除。

如果一个功能不服务 AI 伴侣主线，直接删除。

如果一个功能服务 AI 伴侣但命名来自插件平台，迁移命名和边界后保留能力。

最终目标不是“还能跑”，而是旧架构已经不存在。
