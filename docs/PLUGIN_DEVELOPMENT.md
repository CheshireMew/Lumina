# Lumina 插件开发指南

本文档描述当前真实生效的插件协议。不要再使用旧的 `BaseSystemPlugin + initialize/terminate`，也不要再写旧 SDK 的 `on_load/on_unload/on_enable/on_disable`。

## 目录结构

```text
python_backend/plugins/extensions/
└── my_plugin/
    ├── manifest.yaml
    └── plugin.py
```

## Manifest

`manifest.yaml` 只保留这组稳定字段：

```yaml
id: my_company.my_plugin
api_version: "1.0"
kind: extension
capability: chat.post_processor
runtime_target: main
permissions:
  - eventbus.subscribe
  - eventbus.emit
config_schema: {}
provides:
  - avatar
```

字段含义：

- `id`: 插件唯一标识
- `api_version`: 面向的稳定插件 API 版本
- `kind`: `provider` / `extension` / `gateway` / `processor` / `driver`
- `capability`: 主能力标识
- `runtime_target`: `main` / `worker:stt` / `worker:tts`
- `permissions`: 权限声明
- `config_schema`: 前端配置结构
- `provides`: 附加能力标识

## 生命周期

`plugin.py` 必须导出类名 `Plugin`，并实现统一生命周期：

```python
import logging

from core.interfaces.plugin import Plugin as BasePlugin

logger = logging.getLogger("MyPlugin")


class Plugin(BasePlugin):
    async def load(self, context):
        await super().load(context)

    async def enable(self):
        await super().enable()
        self.context.subscribe("system.tick", self.on_tick)

    async def disable(self):
        await super().disable()

    async def unload(self):
        await super().unload()

    async def health(self):
        return {"status": "ready"}

    def get_metadata(self):
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "My Plugin",
                "description": "What it does",
                "func_tag": "System",
            }
        )
        return metadata

    async def on_tick(self, event):
        logger.info("tick")
```

## Context API

插件上下文只开放这一组能力：

- `context.events`
- `context.subscribe(event, handler)`
- `await context.emit(event, payload)`
- `context.get_config()`
- `context.update_config(key, value)`
- `context.load_data()`
- `context.save_data(data)`
- `context.get_data_dir()`
- `await context.register_route(path, method, handler)`
- `context.find_capability(capability)`
- `context.get_service(name)`
- `context.get_logger(name)`

`context.get_service(name)` 只用于访问内核明确托管的 facade，例如 `llm_manager`。不要跨层直接改别的插件内部状态。

## 能力标识

当前正式 capability 命名：

- `stt`
- `tts`
- `llm`
- `memory`
- `avatar`
- `tool.search`
- `chat.context`
- `chat.post_processor`

系统分发只看 capability，不看实现类名。

## 聊天插槽

如果插件要介入聊天主链，只能注册这 6 个固定 hook：

- `chat.input_preprocess`
- `chat.context_build`
- `chat.tool_resolve`
- `chat.generate`
- `chat.output_filter`
- `chat.post_turn`

不要直接改 `ChatPipeline` 内部状态，也不要跨层去抓别的插件实例。

## LLM Driver Plugins

`llm` 现在分两层：

- `system.llm_core` 负责聊天网关和路由
- `driver.llm.*` 插件负责注册具体 driver type

如果你要新增新的 LLM 类型，不要改 `LLMManager`，直接新增一个 `driver.llm.*` 插件，并在 `enable()` 时把新的 `type` 注册进去。

## 配置与状态

- 用户意图只写入 `config.plugins.desired_state`
- 当前 provider 只写入 `config.plugins.selected_providers`
- 运行态只从 `plugin_state_aggregator` 读取

如果插件需要自己的配置，写到 `config.plugins.settings[plugin_id]`，通过 `context.get_config()` / `context.update_config()` 访问。

## 调试与安装

- `GET /plugins/debug/state` 可以查看插件发现、加载、启用、权限、配置和健康状态。
- `GET /plugins/capabilities` 可以查看 capability 目录。
- `POST /plugins/upload` 支持安装一个 zip 插件包。压缩包内必须只包含一个 `manifest.yaml`，并且不能有路径穿越。
