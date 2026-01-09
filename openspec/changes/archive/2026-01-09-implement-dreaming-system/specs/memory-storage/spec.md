# memory-storage Specification Increment

## 新增需求

### 需求：记忆生命周期状态

Memory 表必须支持以下状态字段 `status`，以管理记忆的递归重构过程：

- `raw`: 原始对话日志，尚未被消化。
- `active`: 已被消化为摘要 (`summary`) 和洞察 (`insight`) 的活跃记忆。
- `pending_reconsolidation`: 活跃记忆被检索命中后，标记为此状态，等待下一次 Dreaming 周期进行重构。
- `consolidated`: 已被融合进新记忆的旧版本，仅作归档保留。

#### 场景：状态流转

- **当** 记忆被创建
- **那么** 状态为 active

### 需求：摘要与洞察字段

Memory 表必须包含 `summary` (事实摘要) 和 `insight` (心理洞察) 字段，不再维护分离的 Knowledge Graph 表结构。

#### 场景：字段验证

- **当** 插入新记忆
- **那么** 包含 summary 和 insight

### 需求：触碰即脏 (Touch-to-Dirt)

当系统检索记忆（Search）并判定某条 `active` 记忆具有高相关性时，必须异步将其状态更新为 `pending_reconsolidation`。

#### 场景：命中标记

- **当** 记忆被检索命中
- **那么** 状态更新为 pending
