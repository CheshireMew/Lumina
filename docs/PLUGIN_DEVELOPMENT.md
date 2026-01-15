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

复制 `plugins/system/_template/` 目录开始开发:

```powershell
Copy-Item -Recurse python_backend/plugins/system/_template python_backend/plugins/system/my_plugin
```

---

## 最佳实践

1. **使用 EventBus** - 避免直接调用其他插件方法,使用事件通信
2. **声明权限** - 只申请需要的最小权限
3. **错误处理** - 捕获异常,不要让插件崩溃影响核心
4. **日志记录** - 使用 `context.get_logger()` 输出调试信息
5. **数据持久化** - 重要状态保存到 `save_data()`
6. **生命周期** - 实现 `start()` 和 `stop()` 方法
