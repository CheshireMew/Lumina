# Lumina Capability Catalog

这份清单按 capability 分类，不按目录分类。内核只看 capability 和 contract，不看具体实现类名。

## Core Capabilities

- `stt`
  - 当前 provider: `driver.stt.sensevoice`
  - 运行时: `worker:stt`
  - 典型操作: 模型切换、转写、音频配置、健康检查

- `tts`
  - 当前 provider: `driver.tts.edge`
  - 运行时: `worker:tts`
  - 典型操作: 语音列表、语音合成、模型切换、健康检查

- `llm`
  - 当前网关: `system.llm_core`
  - 当前 driver types: `driver.llm.openai`, `driver.llm.deepseek`, `driver.llm.gemini`, `driver.llm.pollinations`
  - 运行时: `main`
  - 典型操作: 对话生成、模型列表、工具调用、provider instance 路由

- `memory`
  - 当前 provider: `driver.memory.postgres`
  - 运行时: `main`
  - 典型操作: 写入、检索、上下文拼装、健康检查

- `avatar`
  - 当前插件: `system.avatar_server`
  - 运行时: `main`
  - 典型操作: 情绪同步、模型扫描、前端动画广播

## Chat Pipeline Slots

聊天主链只允许在这 6 个固定节点插入：

- `chat.input_preprocess`
- `chat.context_build`
- `chat.tool_resolve`
- `chat.generate`
- `chat.output_filter`
- `chat.post_turn`

## Derived Capabilities

- `chat.context`
  - 来源: `system.llm_core`, `driver.memory.postgres`, `system.voiceprint`

- `chat.post_processor`
  - 来源: `system.emotion_broker`, `system.avatar_server`

- `tool.search`
  - 当前 provider: `driver.tool.search.brave`, `driver.tool.search.duckduckgo`
  - 运行时: `main`
  - 典型操作: 联网检索、结果摘要

## Discovery APIs

- `GET /plugins/list`
  - 当前插件状态聚合视图

- `GET /plugins/capabilities`
  - capability 维度的能力目录

- `GET /plugins/debug/state`
  - 已发现、已加载、已启用、权限、配置、健康状态

- `GET /plugins/marketplace`
  - marketplace 预留结构，当前仅返回已安装插件与空 discoverable 列表
