# knowledge-graph Specification

## Purpose
TBD - created by archiving change fix-entity-merge-logic. Update Purpose after archive.
## 需求
### 需求：手动实体合并

系统必须提供通过 API 手动合并预定义别名实体的功能。

#### 场景：成功合并别名

- **当** 触发合并操作（通过 API 或 UI）时
- **且** `entity_aliases.json` 中配置了 `"柴郡": "Cheshire"`
- **且** 数据库中同时存在 `entity:柴郡` 和 `entity:Cheshire`
- **那么** 所有指向 `entity:柴郡` 的边（入边和出边）都应重定向到 `entity:Cheshire`
- **且** `entity:柴郡` 节点应被物理删除
- **且** 操作日志应记录合并详情

