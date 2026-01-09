# 变更：Cleanup Legacy Architecture (Remove Qdrant/SQLite)

## 为什么

项目已复架构转向 SurrealDB，但旧代码（Qdrant/SQLite）仍残留在项目中，且被核心服务（如 `memory_server`, `routers/soul`）错误地引用或作为 fallback，导致架构混乱、维护困难及潜在的性能开销。

## 变更内容

- **架构简化**: 移除双层记忆架构中的 Qdrant/SQLite 层，所有长期记忆（向量+图）均由 SurrealDB 接管。
- **依赖解耦**: 从 `LiteMemory` 中提取 Embedding 模型加载这一核心功能，转移至 `ModelManager` 或 `main.py`。
- **代码清理**: 删除/归档所有 `*_legacy.py` 文件及 `LiteMemory` 相关代码。
- **归档**: 将旧代码移动到 `archive/` 目录。
- **依赖移除**: 移除 `qdrant-client` 依赖。

## 影响

- **受影响规范**: `memory-storage`
- **受影响代码**: `main.py`, `memory_server.py`, `routers/soul.py`, `lite_memory.py` (移除)
- **数据**: `lite_memory_db/`, `memory_db/` (归档)
- **风险**: 必须确保 Embedding 模型能独立加载。
