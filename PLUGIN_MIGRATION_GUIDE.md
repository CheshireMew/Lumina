# Lumina 插件迁移指南 (Migration Guide)

**版本**: Architecture 6.0
**日期**: 2026-01-19
**状态**: 强制执行 (Enforced)

本文档旨在指导开发者将旧版本插件（Legacy/V1）迁移到符合 Architecture 6.0 安全与能力契约标准的新架构。

---

## 1. 核心变更概览

| 特性         | 旧版 (Legacy)                     | 新版 (Architecture 6.0)                   |
| :----------- | :-------------------------------- | :---------------------------------------- |
| **依赖管理** | 硬编码路径 / Python Import        | **Capability Contract (能力契约)**        |
| **服务发现** | `services.stt_manager` (直接访问) | `context.find_capability("stt.provider")` |
| **权限控制** | 无 / 默认信任                     | **Manifest 声明 + 运行时阻断**            |
| **上下文**   | `ServiceContainer` (上帝对象)     | `LuminaContext` / `SandboxedContext`      |

---

## 2. Manifest 升级 (`manifest.yaml`)

插件必须明确声明其提供的“能力”和需要的“权限”。

### 2.1 声明能力 (Provides)

如果你的插件提供了系统级服务（如 STT, TTS, 存储），必须填写 `provides`：

```yaml
# 旧版：无此字段
# 新版：
provides:
  - type: stt.provider # 能力类型 (Enum: stt.provider, tts.provider, llm.provider, memory.store, system.extension)
    attributes:
      model: sensevoice # 属性用于过滤
      offline: true
```

### 2.2 声明权限 (Permissions)

默认情况下，插件运行在沙箱中，无法访问网络或文件系统。必须从以下列表中按需申请：

```yaml
permissions:
  - network.outbound # 允许发起 HTTP/WebSocket 请求
  - network.listen # 允许开启端口监听
  - filesystem.external # 允许访问插件数据目录以外的文件
  - plugin.discovery # 允许查找其他插件 (find_capability)
  - ipc.messaging # 允许与其他进程通信
```

---

## 3. 代码迁移指南

### 3.1 移除硬编码依赖

❌ **错误示范 (Legacy)**:

```python
# 依赖特定的目录结构和类名
from plugins.extensions.voiceprint.manager import VoiceprintManager
vp = VoiceprintManager()
```

✅ **正确示范 (Arch 6.0)**:

```python
# 通过能力动态发现
def initialize(self, context: LuminaContext):
    # 1. 查找提供 'voice_security' 特性的插件
    vp_id = context.find_capability("system.extension", feature="voice_security")

    if vp_id:
        # 2. 通过 EventBus 或 Router 交互，而不是直接 import 类
        context.bus.emit("capability.voice.verify", {"audio": data})
```

### 3.2 使用 `LuminaContext`

插件不再能直接访问全局 `services` 对象。所有操作必须通过 `initialize` 传入的 `context` 进行。

```python
class MyPlugin(BaseSystemPlugin):
    def initialize(self, context):
        self.context = context

        # 注册服务
        context.register_service("my_service", self)

        # 注册路由
        context.register_route_def("/api/my", "GET", "handler", self.handler)

        # 访问核心服务
        self.config = context.config
        self.logger = context.get_logger(self.id)
```

### 3.3 处理权限拒绝

如果未声明权限而尝试操作，系统会抛出 `PermissionError` 并记录审计日志 `audit.jsonl`：

> `🛡️ AUDIT ALERT: my_plugin -> AuditAction.SENSITIVE_CALL on permission:network.outbound (denied)`

**调试建议**: 查看 `python_backend/logs/audit/audit.jsonl` 确认被拦截的操作。

---

## 4. 常用能力类型 (CapabilityType)

- `stt.provider`: 语音转文字引擎
- `tts.provider`: 文字转语音引擎
- `llm.provider`: 大语言模型服务
- `memory.store`: 向量/图数据库存储
- `system.extension`: 通用系统扩展 (需配合 `attributes` 使用)

---

**注意**: 不遵守此标准的插件在未来版本中将无法加载或被系统强行禁用。
