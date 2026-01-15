# 变更:修复实体合并逻辑与 UI 交互

## 为什么

用户报告 "Merge & Clean" 功能无法合并重复实体(显示 "Merged: 0"),即使数据库中存在已知的别名与规范实体对(如 `柴郡` -> `Cheshire`)。
为了保持知识图谱的整洁和检索效率,必须修复后端合并逻辑,确保别名节点及其关联边能被正确迁移并删除。

## 变更内容

- **后端修复 (`surreal_memory.py`)**:
  - 实现健壮的 SurrealDB 响应解析(兼容列表与字典包装格式)。
  - 实现安全的 SQL ID 格式化(自动处理非 ASCII 字符的尖括号转义)。
- **工具更新**:
  - 更新 `test_merge.py` 诊断脚本以匹配后端逻辑。

## 影响

- **受影响规范**: `specs/knowledge-graph`
- **受影响组件**: `SurrealMemory` (Backend), `SurrealViewer` (Frontend Button)
