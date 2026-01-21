# Lumina 插件开发指南 (Plugin Development Guide)

本文档介绍如何为 Lumina 开发第三方插件。

---

## 快速开始

### 1. 创建插件目录

```
python_backend/plugins/system/
└── my_plugin/
    ├── manifest.yaml   # 必需:插件元数据
    └── manager.py      # 必需:插件入口
```

### 2. 编写 manifest.yaml

```yaml
id: my_company.my_plugin # 唯一标识符 (小写字母/数字/下划线/点)
version: "1.0.0" # 语义版本
name: "My Awesome Plugin" # 显示名称
description: "What it does" # 简短描述
entrypoint: "manager:MyManager" # 入口格式: module:ClassName
author: "Your Name"
category: "feature" # system / feature / integration
tags: ["tag1", "tag2"]

# 依赖的其他插件 (将按顺序加载)
dependencies: []

# 权限声明 (见 core/permissions.py)
permissions:
  - event.subscribe
  - event.emit
```

### 3. 编写 manager.py

```python
import logging
from typing import Any
from plugins.base import BaseSystemPlugin

logger = logging.getLogger("MyPlugin")

class MyManager(BaseSystemPlugin):

    @property
    def id(self) -> str:
        return "my_company.my_plugin"  # 必须与 manifest.yaml 一致

    @property
    def name(self) -> str:
        return "My Awesome Plugin"

    @property
    def enabled(self) -> bool:
        return True

    def initialize(self, context: Any):
        super().initialize(context)

        # 订阅事件
        context.bus.subscribe("system.tick", self._on_tick)

        # 注册服务供其他插件发现
        context.register_service("my_plugin", self)

        logger.info("✨ My Plugin initialized!")

    def _on_tick(self, event):
        pass  # 每秒调用一次
```

---

## Context API 参考

插件通过 `context` 访问系统能力:

| API                                        | 说明              | 权限要求                    |
| ------------------------------------------ | ----------------- | --------------------------- |
| `context.bus`                              | EventBus 事件总线 | event.subscribe, event.emit |
| `context.soul`                             | 角色管理器        | 无 (只读)                   |
| `context.ticker`                           | 全局计时器        | ticker.subscribe            |
| `context.memory`                           | 记忆系统          | memory.read, memory.write   |
| `context.llm_manager`                      | LLM 管理器        | llm.invoke                  |
| `context.config`                           | 配置管理器        | 无 (只读)                   |
| `context.load_data(id)`                    | 读取插件数据      | 无                          |
| `context.save_data(id, data)`              | 保存插件数据      | filesystem.write            |
| `context.get_data_dir(id)`                 | 获取数据目录      | filesystem.read             |
| `context.register_service(name, instance)` | 注册服务          | 无                          |
| `context.get_logger(name)`                 | 获取日志器        | 无                          |

---

## EventBus 使用

### 订阅事件

```python
# 精确匹配
sub_id = context.bus.subscribe("system.tick", self._on_tick)

# 通配符匹配
sub_id = context.bus.subscribe("plugin.*", self._on_any_plugin_event)
```

### 发布事件

```python
# 异步发布
await context.bus.emit("my_plugin.ready", {"status": "ok"})

# 同步发布 (在非 async 函数中)
context.bus.emit_sync("my_plugin.ready", {"status": "ok"})
```

### 取消订阅

```python
context.bus.unsubscribe(sub_id)
```

### 服务发现

```python
# 注册自己
context.bus.register_service("my_service", self)

# 获取其他服务
other_plugin = context.bus.get_service("heartbeat_service")
if other_plugin:
    other_plugin.do_something()

# 列出所有服务
services = context.bus.list_services()
```

---

## 内置事件类型

| 事件                   | 触发时机          | Payload                  |
| ---------------------- | ----------------- | ------------------------ |
| `system.tick`          | 每秒              | `{timestamp: "ISO8601"}` |
| `system.tick.minute`   | 每分钟            | `{timestamp: "ISO8601"}` |
| `service.registered`   | 服务注册时        | `{name, instance}`       |
| `service.unregistered` | 服务注销时        | `{name}`                 |
| `plugin.loaded`        | 插件加载后        | `{id, instance}`         |
| `plugin.unloaded`      | 插件卸载后        | `{id}`                   |
| `core.register_router` | 注册 FastAPI 路由 | `{router, prefix}`       |

---

## 权限系统

如果你的插件在 `manifest.yaml` 中声明了 `permissions`,系统会使用 `SandboxedContext` 进行权限检查。

### 可用权限

| 权限                  | 说明                 |
| --------------------- | -------------------- |
| `filesystem.read`     | 读取文件             |
| `filesystem.write`    | 写入文件             |
| `filesystem.external` | 访问插件目录外的文件 |
| `network.outbound`    | 发起网络请求         |
| `network.listen`      | 监听网络端口         |
| `memory.read`         | 读取记忆系统         |
| `memory.write`        | 写入记忆系统         |
| `llm.invoke`          | 调用 LLM             |
| `ticker.subscribe`    | 订阅计时器事件       |
| `event.subscribe`     | 订阅系统事件         |
| `event.emit`          | 发布自定义事件       |
| `plugin.discovery`    | 发现其他插件         |

### 权限错误处理

```python
try:
    data = context.memory.query(...)
except PermissionError as e:
    logger.error(f"权限不足: {e}")
```

---

## 数据持久化

### 保存 JSON 数据

```python
# 加载
data = self.load_data()  # 返回 dict

# 修改
data["my_key"] = "my_value"

# 保存
self.save_data(data)
```

数据存储位置: `characters/{character_id}/data/{plugin_id}/data.json`

### 二进制文件

```python
data_dir = self.get_data_dir()  # 返回 Path
my_file = data_dir / "my_file.bin"
with open(my_file, "wb") as f:
    f.write(binary_data)
```

---

## 添加 HTTP 路由

```python
from fastapi import APIRouter

class MyManager(BaseSystemPlugin):

    def initialize(self, context):
        super().initialize(context)

        # 创建路由
        router = APIRouter()

        @router.get("/status")
        def get_status():
            return {"status": "ok"}

        # 通过 EventBus 注册 (推荐)
        self.register_router(router, prefix="/plugins/my_plugin")
```

路由将在 `/plugins/my_plugin/status` 可访问。

---

## 模板插件

使用 CLI 工具快速创建新插件:

```powershell
# 创建新插件
python python_backend/scripts/create_plugin.py my_awesome_plugin

# 指定作者和分类
python python_backend/scripts/create_plugin.py my_company.my_plugin --author "Your Name" --category feature
```

或者手动复制模板:

```powershell
Copy-Item -Recurse python_backend/plugins/system/_template python_backend/plugins/system/my_plugin
```

---

## Worker 驱动插件开发 (高级)

STT/TTS 等驱动插件运行在独立的 Worker 进程中,与主进程通过 HTTP/IPC 通信。

### 1. 驱动 Manifest 配置

```yaml
id: my_tts_driver
version: "1.0.0"
name: "My TTS Driver"
category: "driver"

# 关键: 指定运行在 Worker 进程
runtime_target: "tts_server"

# 必须声明提供的能力
provides:
  - type: "tts.provider"
    attributes:
      language: "zh"
      quality: "high"

# 驱动通常需要互斥 (同时只能启用一个)
group_id: "tts"
group_exclusive: true
```

### 2. 驱动类结构

```python
from core.interfaces.driver import BaseDriver

class MyTTSDriver(BaseDriver):

    @property
    def id(self) -> str:
        return "my_tts_driver"

    async def synthesize(self, text: str, **params) -> bytes:
        """生成语音数据"""
        # 实现 TTS 逻辑
        audio_bytes = await self._call_tts_api(text)
        return audio_bytes

    async def get_voices(self) -> list:
        """返回可用的声音列表"""
        return [{"id": "voice1", "name": "Voice 1"}]
```

### 3. 驱动状态上报

Worker 驱动通过生命周期总线上报状态:

```python
async def on_ready(self):
    """驱动就绪后调用"""
    await self.lifecycle_bus.publish_state(self.id, {
        "active_status": "ready",
        "capabilities": ["tts.provider"]
    })
```

---

## 调试和测试

### 开发模式热重载

```powershell
# 修改代码后重载插件 (无需重启后端)
curl -X POST http://localhost:8010/plugins/reload/my_plugin
```

### 查看插件状态

```powershell
# 列出所有插件
curl http://localhost:8010/plugins/list | python -m json.tool

# 查看性能报告
curl http://localhost:8010/debug/plugin_perf
```

### 常见问题排查

| 症状       | 可能原因               | 解决方案                 |
| ---------- | ---------------------- | ------------------------ |
| 插件不加载 | manifest.yaml 格式错误 | 检查 YAML 语法           |
| 权限错误   | 缺少 permissions 声明  | 在 manifest 添加所需权限 |
| 初始化超时 | initialize() 阻塞      | 使用 async 或后台任务    |
| 事件不触发 | 未订阅或事件名错误     | 检查 subscribe() 调用    |

### 编写测试

```python
# tests/test_my_plugin.py
import pytest
from unittest.mock import MagicMock

def test_my_plugin_init():
    from plugins.extensions.my_plugin.manager import MyPluginManager

    plugin = MyPluginManager()
    mock_context = MagicMock()
    mock_context.bus = MagicMock()

    plugin.initialize(mock_context)

    # 验证订阅了正确的事件
    mock_context.bus.subscribe.assert_called()
```

---

## 性能最佳实践

### 1. 避免阻塞初始化

```python
# ❌ 不好: 阻塞主线程
def initialize(self, context):
    self.data = self.load_large_file()  # 阻塞!

# ✅ 好: 异步加载
async def initialize(self, context):
    super().initialize(context)
    # 后台加载
    asyncio.create_task(self._load_data_async())
```

### 2. 事件处理要快

```python
# ❌ 不好: 事件处理器中做重活
async def _on_tick(self, event):
    result = await self.slow_api_call()  # 每秒调用一次 API!

# ✅ 好: 使用节流
async def _on_tick(self, event):
    if time.time() - self._last_call < 60:  # 每分钟一次
        return
    self._last_call = time.time()
    asyncio.create_task(self._do_work())
```

### 3. 监控你的插件

系统会自动监控插件性能。如果你的插件:

- 初始化超过 1 秒 → 警告日志
- 事件处理超过 100ms → 警告日志
- 事件处理超过 5 秒 → 错误日志 + 超时计数

---

## API 版本和稳定性

Lumina 插件 API 使用语义版本控制:

| 标记                 | 含义     | 承诺             |
| -------------------- | -------- | ---------------- |
| `@api_stable("1.0")` | 稳定 API | 主版本内不变     |
| `@api_experimental`  | 实验性   | 可能随时变化     |
| `@deprecated("2.0")` | 弃用     | 将在指定版本移除 |

在 manifest.yaml 中指定 API 版本:

```yaml
api_version: "1.0" # 你的插件兼容的 API 版本
```

---

## 最佳实践

1. **使用 EventBus** - 避免直接调用其他插件方法,使用事件通信
2. **声明权限** - 只申请需要的最小权限
3. **错误处理** - 捕获异常,不要让插件崩溃影响核心
4. **日志记录** - 使用 `context.get_logger()` 输出调试信息
5. **数据持久化** - 重要状态保存到 `save_data()`
6. **生命周期** - 实现 `initialize()` 和 `terminate()` 方法
7. **性能意识** - 避免阻塞操作,使用异步模式
8. **API 版本** - 在 manifest 中声明 `api_version`
