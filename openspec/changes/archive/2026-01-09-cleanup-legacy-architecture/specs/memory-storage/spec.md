# Memory Storage Specification Increment

## 新增需求

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
