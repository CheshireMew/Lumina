# 前后端架构问题关闭台账（2026-08-23）

本文冻结并关闭本轮架构检查发现的 23 个问题。状态“已关闭”表示旧失效路径已经迁移或退出生产路径，并且至少有静态契约、自动化测试或构建前检查作为证据；它不代表已经执行安装包、外部模型账号或真实音频硬件验收。

## P0：会直接破坏对话、数据或生命周期的根因

| ID | 原问题 | 关闭方式与证据 | 状态 |
| --- | --- | --- | --- |
| ARC-P0-01 | WebSocket 消息缺少客户端、回合和请求确认关系 | `EventPacket` 统一携带 `client_id`、`turn_id`、`trace_id`、`generation`、`sequence_number`；Gateway 按客户端路由并返回 ack/reject；前端请求有有界队列、超时、重连重放和旧代际丢弃。协议与网关测试覆盖。 | 已关闭 |
| ARC-P0-02 | 全局“当前回合”造成多请求互相覆盖 | `CompanionRuntime` 与事件适配器按 `(client_id, session_id, turn_id)` 管理回合；中断也按同一身份定位。并发和聊天场景测试覆盖。 | 已关闭 |
| ARC-P0-03 | 后端历史没有形成前端可恢复链路 | 新增 `/companion/history` 响应模型；`SessionManager` 是真实历史来源；前端按稳定消息 ID 合并历史、推理内容和完成状态，并用请求版本避免旧响应覆盖。 | 已关闭 |
| ARC-P0-04 | LLM 生成参数在配置、流水线和驱动间丢失或错位 | 运行设置统一声明 temperature、top_p、max_tokens、frequency/presence penalty、seed、thinking；`ChatPipeline` 只从 `LLMManager` 取得并传递完整参数；驱动按真实能力消费。流水线与驱动测试覆盖。 | 已关闭 |
| ARC-P0-05 | 配置显示已选择 provider，但运行时实际能力来源不一致 | LLM 与 Memory 都通过 capability/provider 选择；运行状态检查真实驱动和可用能力，不再把“配置存在”当成“能力可用”。provider 选择与运行状态测试覆盖。 | 已关闭 |
| ARC-P0-06 | STT/TTS 暴露未实现或伪造的能力、引擎和音色 | 删除伪引擎别名，STT/TTS 只返回实际发现的 driver/voice；旧 Edge 名称只做明确规范化；TTS 角色音色和韵律进入真实请求。构建前运行时契约检查覆盖。 | 已关闭 |
| ARC-P0-07 | 配置、角色和 Soul 分散写入，失败可能留下半份状态 | 配置加载和 provider/route/audio 更新改为原子写入与失败回滚；角色配置与 Soul 由同一持久化边界合并保存，文件操作放入线程，不再吞掉写入错误。配置与角色测试覆盖。 | 已关闭 |
| ARC-P0-08 | 一轮对话后的历史、记忆和 Soul 副作用不是可恢复事务 | `CompanionInteractionRecorder` 成为唯一后置操作边界；`PostTurnJournal` 逐步记录 history、memory、soul、consolidation 状态，使用稳定 `turn_id` 幂等执行，启动时从失败步骤继续。恢复测试证明历史不会重复写入。 | 已关闭 |
| ARC-P0-09 | 长期记忆使用伪 embedding、重复全表扫描，归并任务不可追踪 | 改用惰性加载的多语言 SentenceTransformer；混合检索只做一次带条件扫描；记忆和归并使用确定性 ID。归并先持久化 `pending` 任务再调用模型，失败可重试，并持续排空达到阈值的未处理回合。记忆真实驱动与崩溃恢复测试覆盖。 | 已关闭 |
| ARC-P0-10 | Tool loop 不能正确处理多工具、参数和终止条件 | `ChatPipeline` 实现有轮数上限的多工具循环，保留工具调用片段和 reasoning，逐个执行并把结构化结果回送模型；异常按回合返回，不再破坏整条流。E2E tool-loop 测试覆盖。 | 已关闭 |
| ARC-P0-11 | 启动失败和退出过程缺少回滚，Worker/连接/后台任务可能泄漏 | Bootstrap 失败按已启动阶段回滚；lifespan 使用 `finally` 关闭；退出顺序覆盖聊天、归并、Gateway、Worker、HTTP、数据库和事件总线；Windows 进程先优雅退出，再结束已确认的进程树。生命周期和进程管理测试覆盖。 | 已关闭 |

## P1：会持续制造耦合、漂移或卡死的问题

| ID | 原问题 | 关闭方式与证据 | 状态 |
| --- | --- | --- | --- |
| ARC-P1-01 | `ServiceContainer`、EventBus、Gateway、Worker Hub 等隐藏全局单例 | 容器只作为显式 composition root 创建并挂到 `app.state.services`；HTTP/WebSocket 从应用状态注入；事件总线、Gateway、Worker Hub 和 Discovery 都由容器构造和传递。容器隔离测试与应用导入检查覆盖。 | 已关闭 |
| ARC-P1-02 | OpenAPI 类型生成了却未真正使用，前端仍以 `any` 和手写结构跨边界 | 后端关键路由补齐响应模型；离线导出 OpenAPI；前端 API 客户端返回 `unknown` 并在边界解析，角色结构显式规范化；生成文件哈希前后一致。 | 已关闭 |
| ARC-P1-03 | EventBus 时间格式不统一，schema 或 handler 错误被隐藏 | 事件时间统一为 epoch；schema 校验和 handler 失败向调用方传播；总线按运行实例构造，不再借全局对象通信。事件契约测试覆盖。 | 已关闭 |
| ARC-P1-04 | Worker 配置下发时序、LIPP 顺序和进程停止语义不稳定 | Worker 先完成控制通道和配置握手再提供能力；LIPP 顺序和运行目标统一；同步进程操作放入线程；Supervisor 和 ProcessManager 都提供可等待的停止流程。Worker、LIPP、进程测试覆盖。 | 已关闭 |
| ARC-P1-05 | TTS 代理整段缓冲、每次新建 HTTP 客户端，首包等待无上限 | 代理复用共享异步客户端并返回真正的 `StreamingResponse`；前端 TTS 请求设置首响应超时并区分用户取消和超时；音频分块直接进入播放队列。TTS 与前端类型检查覆盖。 | 已关闭 |
| ARC-P1-06 | AudioQueue 清空时当前读取和播放 Promise 不结束，Hook 卸载残留资源 | 队列跟踪并取消当前 reader，清理当前音频与 MediaSource，使用 generation 阻止旧流重新启动；Hook 使用惰性稳定实例并在卸载时清理。新增活动流取消测试。 | 已关闭 |
| ARC-P1-07 | 状态轮询使用 `setInterval`，慢请求会重叠且缺少超时 | Runtime/STT 轮询改为一次完成后再安排下一次的 `setTimeout`；公共请求层组合 AbortSignal 并设置超时。扫描确认剩余 interval 仅用于 WebSocket 心跳和 Live2D 空闲动作。 | 已关闭 |
| ARC-P1-08 | `App.tsx` 和 Companion Provider 同时承担过多状态、事件与 UI 责任 | 聊天运行状态、聊天面板、启动状态和 Avatar 事件拆到独立 hook/组件；Provider 只组合运行边界并返回 memoized value；`App.tsx` 回到顶层布局。TypeScript、Lint 和组件测试覆盖。 | 已关闭 |
| ARC-P1-09 | Electron bridge 与消息结构在 main/preload/renderer 多处重复声明 | Electron 桥类型集中到共享契约；聊天消息使用同一稳定结构；main、preload 和 renderer 共同引用，消除跨层手写漂移。TypeScript 编译覆盖。 | 已关闭 |
| ARC-P1-10 | 会话与角色文件同步 I/O、固定临时文件名且没有并发锁 | 文件仓储统一放入 `asyncio.to_thread`；每个目标路径有锁，临时文件名唯一并原子替换；损坏 JSON 明确报错，不再静默返回空数据。仓储、会话和角色测试覆盖。 | 已关闭 |
| ARC-P1-11 | 空壳 automation、重复 registry/discovery、旧 service locator 和 LangChain 残留 | 活跃生命周期移除空壳 automation；被替代的模块原样移入 `docs/archive/backend/` 并记录继任者；旧包不可导入；LangChain 依赖和构建收集项移除；仍在使用的 `generic_worker` 保留并校验。 | 已关闭 |
| ARC-P1-12 | 三套 Python 测试入口割裂，CI 不检查类型漂移且 Lint 覆盖不足 | 根 `pytest.ini` 和 `test:python` 统一收集三套测试；CI 检查生成类型漂移、前端测试/TypeScript/ESLint、Ruff 和全量 Pytest；性能测试在本地服务缺失时快速跳过，不再等待 500 秒。 | 已关闭 |

## 本地验证结果

- `python -m pytest -q -p no:cacheprovider`：542 passed，25 skipped，1 xfailed。
- `npm test`：4 个文件、10 项测试全部通过。
- `npx tsc --noEmit`、`npm run lint`、`python -m ruff check ...`：通过。
- `npm run verify-build`：runtime contract 与 source contract 通过。
- `npm run gen-types`：生成前后 SHA-256 均为 `ED82359F9474E85962C6E0FB7DA30D4BF2C4375BCAC281242C199EBE4A24ED36`。
- `python -m compileall -q python_backend`、后端应用导入、`git diff --check`：通过。

## 证据边界

本轮按用户要求只验收 Windows 当前源码与本地自动化，没有打包，也没有改动或验证远程 CI 的实际运行结果。真实麦克风、声卡、Live2D 窗口、外部 LLM/STT/TTS 账号与网络链路仍属于运行环境验收，不把它们伪装成本轮已经取得的代码证据。
