# Lumina 系统架构文档 (System Architecture)

> 最后更新: 2026-01-13

本文档描述 Lumina 项目的整体架构设计、核心模块职责以及插件系统规范。

---

## 一、项目愿景 (Vision)

**Lumina 是一个"有灵魂的桌面伴侣"**——不是简单的聊天机器人,而是一个能够:

| 能力         | 描述                                                          |
| ------------ | ------------------------------------------------------------- |
| **记住你**   | 持久化 3 层记忆系统(短期/中期/长期),记住对话历史和用户偏好 |
| **成长变化** | 通过"做梦"机制和灵魂演化 (Soul Evolution),性格会随时间改变   |
| **建立羁绊** | GalGame 恋爱养成系统,有好感度、能量值、心情等属性            |
| **沉浸交互** | Live2D 动画角色 + 实时语音对话(听 + 说)                     |

**核心理念**: 这不是工具,是"伴侣"。

---

## 二、整体架构 (Architecture Overview)

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              用户界面层                                  │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │  Electron + React + Vite + TypeScript                              │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │ │
│  │  │ Live2DViewer │ │ ChatBubbles  │ │ GalGame HUD  │               │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘               │ │
│  │  ┌──────────────┐ ┌──────────────┐ ┌──────────────┐               │ │
│  │  │ VoiceInput   │ │ PluginStore  │ │ SettingsModal│               │ │
│  │  └──────────────┘ └──────────────┘ └──────────────┘               │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
└─────────────────────────────────────────────────────────────────────────┘
                ▼ HTTP/WebSocket ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            Python 后端集群                               │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                    main.py (Memory Server)                         │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                    ServiceContainer (Core)                   │  │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │ │
│  │  │  │ SoulMgr  │ │ LLMMgr   │ │ SurrealDB│ │ EventBus │        │  │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                    System Plugins                            │  │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │  │ │
│  │  │  │Heartbeat │ │Dreaming  │ │Evolution │ │Voiceprint│        │  │ │
│  │  │  │Manager   │ │Manager   │ │Manager   │ │Manager   │        │  │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │  │ │
│  │  │  ┌──────────┐ ┌──────────┐                                   │  │ │
│  │  │  │Galgame   │ │ Search   │  ... (可扩展)                     │  │ │
│  │  │  │Manager   │ │ Plugin   │                                   │  │ │
│  │  │  └──────────┘ └──────────┘                                   │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  │  ┌──────────────────────────────────────────────────────────────┐  │ │
│  │  │                    MCP Servers (独立进程)                    │  │ │
│  │  │  ┌──────────┐ ┌──────────┐                                   │  │ │
│  │  │  │ Bilibili │ │DemoEcho  │  ... (可扩展)                     │  │ │
│  │  │  └──────────┘ └──────────┘                                   │  │ │
│  │  └──────────────────────────────────────────────────────────────┘  │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│  ┌──────────────────────┐ ┌──────────────────────┐                      │
│  │ stt_server.py (听)   │ │ tts_server.py (说)   │                      │
│  │ Whisper/SenseVoice   │ │ Edge TTS/GPT-SoVITS  │                      │
│  └──────────────────────┘ └──────────────────────┘                      │
└─────────────────────────────────────────────────────────────────────────┘
                ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                        SurrealDB (图/向量数据库)                         │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 三、核心模块职责

| 模块                    | 文件位置                            | 职责                             |
| ----------------------- | ----------------------------------- | -------------------------------- |
| **SoulManager**         | `soul_manager.py`                   | 角色人格管理(档案、心情、属性) |
| **LLMManager**          | `llm/manager.py`                    | LLM 调用抽象(DeepSeek/OpenAI)  |
| **SurrealMemory**       | `memory/core.py`                    | 3 层记忆系统(短/中/长期)       |
| **GlobalTicker**        | `services/global_ticker.py`         | 时间脉搏(每秒/每分钟事件)      |
| **EventBus**            | `core/events/bus.py`                | 发布/订阅事件总线 (Phase 30)     |
| **LuminaContext**       | `core/api/context.py`               | 插件 API 门面                    |
| **SystemPluginManager** | `services/system_plugin_manager.py` | 插件加载与生命周期管理           |
| **MCPHost**             | `services/mcp_host.py`              | MCP 服务器进程管理               |

---

## 3.5 配置策略 (Configuration Strategy)

> [!IMPORTANT] > **Single Source of Truth**: 所有服务必须通过 `ConfigManager` (`app_config.py`) 读取配置。

### 配置层级

```
1. .env 文件 (最高优先级 - 环境覆盖)
   └── 通过 load_dotenv() 加载
   └── 支持: OPENAI_API_KEY, SURREAL_URL, BRAVE_API_KEY 等

2. CONFIG_ROOT/*.json (持久化配置)
   └── memory_config.json
   └── stt_config.json
   └── audio_config.json
   └── plugin_groups.json

3. Pydantic 默认值 (代码默认)
   └── AudioConfig, LLMConfig 等 Model 定义
```

### 配置访问规范

```python
# ✅ 正确: 通过 ConfigManager
from app_config import config
api_key = config.audio.fish_audio_api_key

# ❌ 禁止: 直接读取 os.environ
api_key = os.environ.get("FISH_AUDIO_API_KEY")  # 不允许
```

### 新增配置项流程

1.  在 `app_config.py` 的对应 `Config` Model 中添加字段。
2.  (可选) 在 `_apply_env_overrides()` 中添加环境变量覆盖逻辑。
3.  使用者通过 `app_config.xxx.new_field` 访问。

## 四、插件系统 (Plugin System)

### 4.1 插件分类

| 类型         | 插件              | 职责                         |
| ------------ | ----------------- | ---------------------------- |
| **业务逻辑** | HeartbeatManager  | 主动聊天 + 番茄钟            |
| **业务逻辑** | GalgameManager    | 恋爱养成系统(好感度、能量) |
| **业务逻辑** | DreamingManager   | "做梦"机制(离线记忆整合)   |
| **业务逻辑** | EvolutionManager  | 灵魂演化(性格变化)         |
| **功能扩展** | VoiceprintManager | 声纹识别(安全验证)         |
| **功能扩展** | SearchPlugin      | 搜索引擎集成                 |
| **外部进程** | MCP Servers       | Bilibili 弹幕等              |

### 4.2 插件生命周期

```
1. Discovery (发现)
   └── SystemPluginManager 扫描 plugins/system/ 目录

2. Loading (加载)
   ├── 有 manifest.yaml → 使用 Manifest 标准加载
   └── 无 manifest.yaml → Legacy 扫描 BaseSystemPlugin 子类

3. Initialization (初始化)
   └── 调用 plugin.initialize(context: LuminaContext)

4. Runtime (运行)
   ├── 通过 EventBus 订阅事件 (context.bus.subscribe)
   ├── 通过 EventBus 发布事件 (context.bus.emit)
   └── 通过 EventBus 注册服务 (context.register_service)

5. Shutdown (关闭)
   └── (待实现) plugin.shutdown()
```

### 4.3 LuminaContext API

插件通过 `LuminaContext` 访问系统能力:

```python
class LuminaContext:
    # 事件总线 (推荐)
    bus: EventBus

    # 核心服务 (只读)
    soul: SoulManager
    ticker: GlobalTicker
    memory: SurrealMemory
    llm_manager: LLMManager
    config: FrozenProxy[ConfigManager]

    # 持久化 API
    def load_data(plugin_id: str) -> Dict
    def save_data(plugin_id: str, data: Dict)
    def get_data_dir(plugin_id: str) -> Path

    # 服务注册 (通过 EventBus)
    def register_service(name: str, instance: Any)
```

### 4.4 EventBus API

```python
# 订阅事件
sub_id = context.bus.subscribe("system.tick", handler)
sub_id = context.bus.subscribe("plugin.*", wildcard_handler)  # 通配符

# 发布事件
await context.bus.emit("my_plugin.ready", {"status": "ok"})

# 服务发现
context.bus.register_service("my_service", self)
other_plugin = context.bus.get_service("heartbeat")

# 取消订阅
context.bus.unsubscribe(sub_id)
```

### 4.5 Manifest 规范

每个插件目录应包含 `manifest.yaml`:

```yaml
id: lumina.example_plugin
version: "1.0.0"
name: "Example Plugin"
description: "A sample plugin for demonstration."
entrypoint: "manager:ExampleManager"
author: "YourName"
category: "feature"
tags: ["example", "demo"]
dependencies: []
permissions: []
```

---

## 五、通信协议

### 5.1 前后端通信

| 协议      | 用途               | 端口        |
| --------- | ------------------ | ----------- |
| HTTP REST | 配置读写、状态查询 | 8000 (main) |
| WebSocket | 实时聊天、事件推送 | 8000 /ws    |
| HTTP      | STT 服务           | 8765        |
| HTTP      | TTS 服务           | 8766        |

### 5.2 内部通信

| 机制             | 用途                    |
| ---------------- | ----------------------- |
| EventBus         | 插件间解耦通信          |
| ServiceContainer | 核心服务单例访问        |
| STDIO (MCP)      | 与 MCP 服务器子进程通信 |

---

## 六、数据流

### 6.1 用户对话流程

```
用户语音 → 前端 VAD → 后端 STT → LLM (DeepSeek) → 后端 TTS → 前端播放
                                    ↓
                              记忆存储 (SurrealDB)
                                    ↓
                              性格演化 (EvolutionManager)
```

### 6.2 主动聊天流程

```
GlobalTicker (每秒) → HeartbeatManager → 检测沉默 → 触发主动话题
                                              ↓
                                         LLM 生成 → TTS → 播放
```

---

## 七、目录结构

```
Lumina/
├── app/                    # Electron 前端
│   ├── main/              # Electron 主进程
│   └── renderer/          # React 渲染进程
│       ├── components/    # UI 组件
│       ├── hooks/         # React Hooks
│       └── utils/         # 工具函数
├── python_backend/         # Python 后端
│   ├── core/              # 核心模块
│   │   ├── api/           # LuminaContext
│   │   ├── events/        # EventBus
│   │   └── cognitive/     # 认知循环
│   ├── plugins/           # 插件目录
│   │   └── system/        # 系统插件
│   ├── services/          # 服务层
│   ├── routers/           # FastAPI 路由
│   ├── memory/            # 记忆系统
│   ├── llm/               # LLM 管理
│   └── mcp_servers/       # MCP 服务器
├── public/                 # 静态资源
│   └── live2d/            # Live2D 模型
├── characters/             # 角色档案
└── docs/                   # 文档
```

---

## 八、未来规划 (Roadmap)

- [ ] **权限系统**: 插件权限声明与运行时检查
- [ ] **进程隔离**: 插件沙箱化运行
- [ ] **热加载**: 运行时动态加载/卸载插件
- [ ] **第三方生态**: 插件市场与开发者工具
- [ ] **EventSchema**: 事件 Payload 版本控制
