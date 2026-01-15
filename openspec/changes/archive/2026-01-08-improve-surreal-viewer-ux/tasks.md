## 1. 修复 Visual Graph 加载问题

- [x] 1.1 修改 `useEffect` 依赖,当 `activeTab === 'graph'` 时触发 `loadGraph()`。
- [x] 1.2 验证:首次点击 Visual Graph 即可显示图谱。

## 2. 添加数据详情弹窗

- [x] 2.1 添加 `detailEdge` 状态变量。
- [x] 2.2 在 Knowledge Data 列表的每一行添加 `onClick` 事件和悬停效果。
- [x] 2.3 点击后弹出 Modal 显示完整 JSON(格式化)。
- [x] 2.4 验证:点击任意关系卡片可查看 `reason`, `context`, `strength` 等字段。

## 3. 改进 Knowledge Data 卡片显示(可选)

- [x] 3.1 在卡片右侧添加 "›" 图标提示可点击。
- [ ] 3.2 考虑在卡片底部显示 `strength` 进度条(可选,未实施)。
