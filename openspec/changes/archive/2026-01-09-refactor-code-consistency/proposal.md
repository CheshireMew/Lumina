# 变更:Refactor Code Consistency

## 为什么

当前代码库存在参数命名不一致和中英文术语混用的情况,这增加了维护难度和误解风险。
具体问题包括:

1. **Request Models**: `AddMemoryRequest` 等请求体中同时出现 `character_id` 和 `char_name` (缩写与全称混用)。
2. **Terminology**: 文档和代码中混用 `fact` 和 `memory`。
3. **Legacy**: 存在过时的参数如 `agent_id`。

## 变更内容

- **API Schemas**: 将 `char_name` 统一为 `character_name` (保持与 `character_id` 命名风格一致)。
- **Docstrings**: 清理所有 Docstrings,将 `fact` 统一替换为 `memory`,除非特指 Knowledge Graph 三元组。
- **Variables**: 在 `routers/memory.py` 等文件中,将局部变量 `char_name` 重构为 `character_name`。

## 影响

- **受影响代码**:
  - `python_backend/schemas/requests.py`
  - `python_backend/routers/memory.py`
  - `python_backend/surreal_memory.py` (Docstrings)
  - `python_backend/routers/soul.py` (引用 user_name)
- **API Compatibility**:
  - Frontend (`core/memory/memory_service.ts`) 硬编码发送 `char_name` 和 `user_id: "user"`。
  - 后端**必须**保留 `alias="char_name"` 以防止前端请求失败。
  - 长期建议:在后续前端重构中更新 TS 定义,但本次 Proposal 仅聚焦后端兼容性重构。

## 其他发现 (Additional Findings)

1. **Default Value Risk**:

   - `schemas/requests.py` 中 `character_id` 默认为 "hiyori"。如果 Client 未发送该字段,可能导致数据错写进 "hiyori" 账号(即使服务器意图服务于 "lillian")。
   - **建议**: 将 Schema 中的默认值移除,改为 `Optional[str] = None`,并在 Router 层回溯到 Server Config 中的 `character_id`。

2. **Date Field Inconsistency**:
   - DB 使用 `created_at`。
   - Frontend 兼容 `timestamp` 或 `created_at`。
   - Legacy 代码混用两者。
   - **建议**: API 响应统一字段名为 `created_at`。
