# Architecture Design: Single-Layer SurrealDB Memory

## Context

当前系统存在两套记忆/向量存储机制:

1. **Legacy**: `LiteMemory` (Wrapper around SQLite + Qdrant).
2. **Modern**: `SurrealMemory` (SurrealDB Native Vector + Graph).

问题在于 `main.py` 和 `memory_server.py` 仍然混合使用两者,特别是 `Embedding Model (SentenceTransformer)` 的加载与管理被绑定在 `LiteMemory` 类中,导致即使只使用 SurrealDB 也必须初始化 LiteMemory(连带创建 SQLite 文件和 Qdrant 连接)。

## Design Decisions

### 1. Centralized Model Management

- **当前**: `memory_clients[id] = LiteMemory(...)` -> `self.model = SentenceTransformer(...)`.
- **变更**: 将模型加载逻辑移入 `ModelManager` (或直接在 `main.py` 使用 `ModelManager` 下载后加载)。
- **新流程**:
  1. `ModelManager` 确保模型文件存在。
  2. `main.py` 启动时加载全局单例 `embedding_model`。
  3. 将 `embedding_model.encode` 函数注入到 `SurrealMemory` 实例中。
  4. 其他服务(如 `routers/debug.py`)如果需要 embedding,直接引用全局模型或通过 `SurrealMemory` 代理,不再通过 `LiteMemory`。

### 2. Removal of Fallback Layers

- `memory_server.py` 和 `routers/memory.py` 中的 `try...except... fallback to LiteMemory` 逻辑将被彻底移除。
- 系统必须完全依赖 SurrealDB。如果 SurrealDB 不可用,系统应报错而非降级到过时数据库。

### 3. Archival Strategy

- 创建根目录 `archive/` (或 `python_backend/archive`?) -> 用户指定 "把旧的代码和旧的文件同一移到归档文件和文件夹中"。
- 决定在 `python_backend` 下创建 `archive_legacy` 文件夹,以保持目录整洁。
- 移动列表:
  - `lite_memory.py`
  - `time_indexed_memory.py`
  - `*_legacy.py`
  - `lite_memory_db/` (Dir)
  - `memory_db/` (Dir)
  - `lumina_memory.db`

## Verification

- **Build Verification**: 系统能在不安装 `qdrant-client` 的情况下启动。
- **Functionality Verification**: `/memory/search` 和 `/soul/switch_character` 在无 `LiteMemory` 情况下正常工作。
