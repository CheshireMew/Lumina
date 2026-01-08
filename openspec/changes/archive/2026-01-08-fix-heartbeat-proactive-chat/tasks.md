## 1. 审查 HeartbeatService 多角色切换逻辑

- [x] 1.1 确认 `/configure` 端点重启 HeartbeatService 时正确切换 SoulManager 实例
- [x] 1.2 验证 `pending_interaction` 标记在角色切换后被正确重置（启动时调用 update_last_interaction）

## 2. 迁移 Inspiration 到 SurrealDB

- [x] 2.1 在 `SurrealMemory` 中添加 `get_random_inspiration()` 方法
- [x] 2.2 从知识图谱的边（facts）中随机获取事实
- [x] 2.3 更新 `/memory/inspiration` API 使用 SurrealDB（优先）并回退 SQLite

## 3. 验证完整流程

- [ ] 3.1 确认前端如何读取 `pending_interaction` 状态
- [ ] 3.2 确认前端如何生成主动对话消息
- [ ] 3.3 端到端测试：沉默 -> 触发 -> 主动消息
