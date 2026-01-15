# 变更:改进 SurrealViewer 用户体验

## 为什么

用户报告了两个 Bug 和一个功能需求:

1. **Visual Graph 首次加载失败**: 只有先点击 "Knowledge Data" 再切回 "Visual Graph" 才能显示图谱。
2. **Knowledge Data 显示不完整**: 只显示三元组 (Subject-Relation-Object),缺少 `reason`, `context`, `strength` 等重要字段。
3. **缺乏详情查看**: 无法点击单条数据查看完整记录。

## 变更内容

- **Bug Fix**: 修复 Graph Tab 初次加载时 `loadGraph()` 不触发的问题(当前触发条件依赖 `selectedTable` 而非 `activeTab`)。
- **Feature**: 在 Knowledge Data 列表中点击任意一行,弹出 Modal 显示完整 JSON 数据(包含所有字段)。
- **UI Polish**: 确保 Knowledge Data 卡片显示更多关键字段(或提示用户点击查看详情)。

## 影响

- **受影响规范**: `specs/surreal-viewer` (新建)
- **受影响组件**: `SurrealViewer.tsx` (Frontend)
