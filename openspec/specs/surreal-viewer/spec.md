# surreal-viewer Specification

## Purpose
TBD - created by archiving change improve-surreal-viewer-ux. Update Purpose after archive.
## 需求
### 需求：Visual Graph 首次加载

系统必须在用户首次选择 "Visual Graph" 标签时自动加载并显示知识图谱。

#### 场景：首次点击 Visual Graph

- **当** 用户打开 SurrealViewer 并首次点击 "Visual Graph" 标签
- **那么** 系统应自动调用 `loadGraph()`
- **且** 显示知识图谱可视化

---

### 需求：知识数据详情查看

用户必须能够点击 Knowledge Data 列表中的任意一条记录，查看其完整的数据详情。

#### 场景：点击关系卡片查看详情

- **当** 用户点击 Knowledge Data 列表中的一条关系记录
- **那么** 系统应弹出一个 Modal 对话框
- **且** Modal 中以格式化 JSON 形式显示该记录的所有字段（包括 `id`, `in`, `out`, `reason`, `context`, `strength`, `created_at` 等）

