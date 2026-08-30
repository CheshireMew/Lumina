# 架构内聚与耦合问题关闭台账（2026-08-24）

## 审计范围与结论

本轮只关闭已经冻结的 F01-F09：依赖边界、重复真源、私有状态穿透、前端职责过载、平行接口、重复请求模型、SQL 校验漂移、不合理硬编码，以及重复状态和资源清理逻辑。审计根为 `D:\Code\Lumina`，基线提交为 `4254e803`，证据对应 2026-08-24 的当前本地工作树。工作树在本轮开始前已有大量未提交改动，因此本台账不把整个工作树描述成一份可直接合并的独立变更集。

根因不是单个文件过长，而是同一事实曾有多个生产者，同时业务服务接收了过宽的运行时对象。治理后，运行时能力、端口映射、请求模型、默认值和 SQL 校验分别只有一个权威来源；业务服务只接收实际使用的依赖；前端协议、运行时投影、模型控制和资源生命周期各自有明确所有者。F01-F09 在本地源码与自动化证据平面全部关闭。

## 发现关闭账本

| ID | 原问题与根因 | 当前唯一责任边界 | 旧路径退出与当前证据 | 本地状态 |
| --- | --- | --- | --- | --- |
| F01 | 全局 service locator 和过宽容器参数隐藏依赖 | `create_service_container()` 只在应用、后端启动器和 Worker 宿主的 composition root 创建容器；业务服务使用显式构造参数 | 生产代码已无 `from services.container import services`；架构守卫验证全局对象不存在，服务构造器不接受容器 | 已解决 |
| F02 | 能力、运行目标和端口在多处分别声明 | `config/worker-runtimes.json` 的 `capabilityContracts` | `core.runtime`、`WorkerRuntimeRegistry`、启动注册和端口解析共同消费目录；公开运行时验证器检查能力、运行时和 `ports.json` 的交叉引用 | 已解决 |
| F03 | 服务直接读取其它对象私有字段 | `LLMManager`、`MemoryService`、`ConfigManager` 的公开状态与更新方法 | 配置、provider 和 runtime 服务只调用公开 API；架构守卫禁止已治理边界重新出现私有穿透 | 已解决 |
| F04 | Gateway、Companion Provider 和 Live2D 渲染器同时拥有多种生命周期 | 传输、请求队列、协议分发、运行时投影、历史同步、角色声音和模型控制分别由独立模块负责 | 原入口只负责编排；TypeScript、ESLint 和前端测试通过；剩余大文件复核未发现多个无关变化原因 | 已解决 |
| F05 | Memory 与搜索存在平行接口定义 | `BaseMemoryDriver` 和 `core.interfaces.search.SearchProvider` | 生产代码只消费规范接口；`VectorDBInterface` 仅保留无逻辑的兼容别名；搜索协议只有一个类定义 | 已解决 |
| F06 | Worker 与主进程代理重复声明 STT/TTS 请求模型 | `python_backend/schemas/api_contracts.py` | 两侧导入同一类对象；身份测试覆盖四个请求模型；OpenAPI 类型已重新生成 | 已解决 |
| F07 | SQLite 与 PostgreSQL 各自校验 SQL 标识符，规则漂移 | `python_backend/core/db/sql_identifiers.py` | 两个驱动共同消费相同校验；PostgreSQL 旧模块只重新导出；合同测试覆盖合法值、非法值和排序方向 | 已解决 |
| F08 | TTS、产品名、消息上限和 Live2D 行为散落硬编码 | 后端 `config/defaults.py`、前端 `app/shared/productDefaults.ts`、角色 `config.json` | 通用默认值集中；模型特有行为由角色配置传给前端；扫描剩余 `Hiyori` 和参数 ID 只位于实例配置、别名/情感映射或规范默认源 | 已解决 |
| F09 | Gateway 请求状态、音频释放、Live2D 视图状态和聊天裁剪重复实现 | `gatewayRequestQueue`、`AudioPlaybackResources`、`viewState`、Zustand store | 调用方只做编排；取消、URL/reader/MediaSource 清理和代际隔离集中；前端音频取消测试及完整类型检查通过 | 已解决 |

## 上帝模块复核

最新扫描中超过 350 行的源码只有六个候选。`sqlite_driver.py` 是单一数据库适配器，`memory/core.py` 是单一记忆领域服务，`gateway.py` 是单一 WebSocket 协议边界，`bus.py` 是单一事件总线，`worker_control_client.py` 是单一 Worker 控制连接，`LLMConfig/styles.ts` 只保存同一组件族的样式资源。它们的方法和依赖都围绕各自同一生命周期或变化原因，未形成跨领域决策中心，因此不按行数机械拆分。此前实际承担多种职责的 Gateway 前端、Companion Provider、Live2D Renderer 和 AudioQueue 已完成拆分。

## 新鲜验证证据

- `D:\Tools\Python310\python.exe -m pytest -q -p no:cacheprovider`：554 passed，25 skipped，1 xfailed。
- 架构、运行时目录、SQL 合同和角色配置专项：16 passed。
- `npm test`：4 个文件、10 项测试通过。
- `npx tsc --noEmit`、`npm run lint -- --no-cache`、Ruff：通过。
- `npm run gen-types`：成功生成当前 OpenAPI TypeScript 类型。
- `npm run verify-build` 与 `npm run verify-runtime-contract`：公开验证入口通过，并实际消费当前运行时能力目录。
- 负向残留扫描：旧全局容器导入、指定业务服务的依赖私有字段访问均为零；STT/TTS 请求模型只在共享 schema 中定义。

## 证据边界

本轮是活跃开发工作树的 Windows 本机源码治理，不包含安装包、远程 CI、远端分支、其它平台、真实外部模型账号、音频硬件或完整桌面交互验收。项目规则明确不允许擅自打包，所以没有用打包结果冒充源码治理证据。上述外部平面均为本轮明确排除，而不是已验证。
