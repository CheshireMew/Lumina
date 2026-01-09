# Refactor Specification

## 新增需求

### 需求：参数命名一致性

必须在所有 API Request Models 中使用全称 `character_name` 而非缩写 `char_name`，以匹配 `character_id` 的命名惯例。
为保持现有客户端兼容性，**必须** 使用 Pydantic 的 alias 功能支持旧名称。

#### 场景：字段解析

- **当** 客户端发送 `char_name` (旧)
- **那么** 后端应能正确将其解析为 `character_name` 字段

### 需求：术语统一

代码注释和内部变量名**必须**优先使用 `memory` 指代存储单元，废弃 `fact`（除非指代特定的三元组结构）和 `fragment`。

#### 场景：代码可读性

- **当** 开发者阅读 `surreal_memory.py` 文档
- **那么** 不应看到 `fact_id` 指代普通 vector memory 的情况
