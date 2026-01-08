# 设计决策：实体合并修复

## 上下文

知识图谱中存在因为 OCR 或 STT 导致的同义实体（如 `柴郡` vs `Cheshire`）。我们需要将它们合并。
`entity_aliases.json` 定义了映射规则。前端有一个按钮触发 `/debug/memory/merge_entities`。

## 问题诊断与尝试过程 (Attempted Methods)

### 1. 初始实现 (Failure: "Merged: 0")

- **方法**: 直接使用 `entity:{alias}` 作为 ID 进行查找和操作。
- **问题**: 数据库中 ID 格式不一致（有时包含括号，有时没有），且直接字符串拼接可能导致 SQL 语法错误。

### 2. 基于名称的查找 (Failure: "Merged: 0")

- **方法**: 使用 `SELECT id FROM entity WHERE name = '{alias}'`。
- **验证**: 创建 `test_merge.py` 脚本，确认可以通过名称找到实体。
- **新问题**: 后端代码在处理 SDK 返回结果时抛出 `KeyError: 'result'`。

### 3. 响应解析修复 (Bug Fix 1)

- **发现**: 新版 Python SurrealDB SDK 的 `query()` 方法直接返回数据列表，而不是旧版的 `{'result': [...]}` 包装器。
- **决策**: 实现 `parse_res(res)` 辅助函数，智能检测并提取结果，兼容两种格式。
- **结果**: `test_merge.py` 成功获取并打印 ID `entity:柴郡`。

### 4. ID 格式化与转义 (Bug Fix 2 - Final)

- **发现**: 即使找到了 ID，合并操作仍然失败。
- **根因**: Python `str(RecordID)` 转换生成的字符串（如 `entity:柴郡`）直接拼接到 SQL `UPDATE` 语句中是非法的。SurrealDB 要求包含非 ASCII 字符的 ID 必须用尖括号包裹（`entity:⟨柴郡⟩`）。
- **决策**: 实现 `safe_id(id_val)` 辅助函数，检测并自动为 ID 添加 `⟨ ⟩`。
- **当前状态**: 已将此修复应用到 `surreal_memory.py`，等待用户最终验证。

## 最终方案

在 `merge_entity_duplicates` 方法中集成以下两个 helper：

1. `parse_res`: 确保总是能拿回数据列表。
2. `safe_id`: 确保生成的 SQL 语句（尤其是 `UPDATE edge SET in=...`）语法正确。
