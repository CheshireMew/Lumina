# memory-storage Specification

## Purpose
TBD - created by archiving change cleanup-legacy-architecture. Update Purpose after archive.
## 需求
### 需求:单一数据源

系统必须且仅能使用 SurrealDB 作为长期记忆(对话日志、向量嵌入和知识图谱)的存储后端。

#### 场景:向量检索

- **当** 请求检索相关记忆(`/search` 或 `/context`)时
- **那么** 系统必须通过 `SurrealMemory` 执行混合检索
- **且** 如果 SurrealDB 不可用,系统应返回错误而非降级到其他存储

### 需求:Embedding 模型加载

系统必须在主进程中统一管理 Embedding 模型,而非在存储适配器内部加载。

#### 场景:模型注入

- **当** 系统初始化 `SurrealMemory` 时
- **那么** 必须注入一个已加载的 Encoder 函数
- **且** `SurrealMemory` 不应自行实例化模型加载器

### 需求:记忆生命周期状态

Memory 表必须支持以下状态字段 `status`,以管理记忆的递归重构过程:

- `raw`: 原始对话日志,尚未被消化。
- `active`: 已被消化为摘要 (`summary`) 和洞察 (`insight`) 的活跃记忆。
- `pending_reconsolidation`: 活跃记忆被检索命中后,标记为此状态,等待下一次 Dreaming 周期进行重构。
- `consolidated`: 已被融合进新记忆的旧版本,仅作归档保留。

#### 场景:状态流转

- **当** 记忆被创建
- **那么** 状态为 active

### 需求:摘要与洞察字段

Memory 表必须包含 `summary` (事实摘要) 和 `insight` (心理洞察) 字段,不再维护分离的 Knowledge Graph 表结构。

#### 场景:字段验证

- **当** 插入新记忆
- **那么** 包含 summary 和 insight

### 需求:触碰即脏 (Touch-to-Dirt)

当系统检索记忆(Search)并判定某条 `active` 记忆具有高相关性时,必须异步将其状态更新为 `pending_reconsolidation`。

#### 场景:命中标记

- **当** 记忆被检索命中
- **那么** 状态更新为 pending

