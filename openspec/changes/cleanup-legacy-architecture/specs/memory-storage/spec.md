# Memory Storage Specification Increment

## 移除需求

### 需求：多层记忆架构支持

**原因**：统一使用 SurrealDB 作为唯一后端，简化架构并移除冗余的 Qdrant/SQLite 依赖。
**迁移**：系统启动时不再初始化 LiteMemory，相关数据归档。

#### 场景：不再初始化 LiteMemory

- **当** 系统启动或切换角色时
- **那么** 不应尝试连接 Qdrant 或创建 SQLite 文件
- **且** 应仅初始化 SurrealDB 连接

## 新增需求

### 需求：单一数据源

系统必须且仅能使用 SurrealDB 作为长期记忆（对话日志、向量嵌入和知识图谱）的存储后端。

#### 场景：向量检索

- **当** 请求检索相关记忆（`/search` 或 `/context`）时
- **那么** 系统必须通过 `SurrealMemory` 执行混合检索
- **且** 如果 SurrealDB 不可用，系统应返回错误而非降级到其他存储

### 需求：Embedding 模型加载

系统必须在主进程中统一管理 Embedding 模型，而非在存储适配器内部加载。

#### 场景：模型注入

- **当** 系统初始化 `SurrealMemory` 时
- **那么** 必须注入一个已加载的 Encoder 函数
- **且** `SurrealMemory` 不应自行实例化模型加载器
