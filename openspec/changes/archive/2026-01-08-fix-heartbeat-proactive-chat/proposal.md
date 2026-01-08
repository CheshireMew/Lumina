# 变更：修复 Heartbeat 主动对话功能

## 为什么

用户报告主动对话功能（AI 在用户沉默 X 分钟后主动搭话）存在问题：

1. **多角色切换问题**: 需验证 HeartbeatService 在角色切换后是否正确重置。
2. **旧数据库检索**: `get_random_inspiration()` 使用 SQLite `facts_staging` 表，需迁移到 SurrealDB 知识图谱。
3. **功能完整性**: 确保整个流程（idle -> pending_interaction -> proactive message）正常工作。

## 经审查发现

### 当前流程 (已确认正确的部分)

1. `HeartbeatService._pulse()` 每 10 秒检查空闲时间
2. 空闲超过阈值 -> `set_pending_interaction(True, reason="idle_timeout")`
3. 标记写入 `galgame.pending_interaction` in `state.json`
4. `/configure` 端点会重启 HeartbeatService (lines 277-284 in memory_server.py) ✅

### 需修复的问题

1. **Inspiration API**: `/memory/inspiration` 调用 `lite_memory.get_random_inspiration()`，使用 SQLite 而非 SurrealDB
2. **前端消费**: 需确认前端如何读取 `pending_interaction` 并生成主动消息

## 变更内容

- **迁移 Inspiration 到 SurrealDB**: 创建 `SurrealMemory.get_random_inspiration()` 方法从知识图谱获取随机事实
- **更新 API**: `/memory/inspiration` 优先使用 SurrealDB，回退到 SQLite
- **验证流程**: 确保多角色切换后主动对话正常工作

## 影响

- **受影响规范**: `specs/heartbeat` (新建)
- **受影响组件**: `surreal_memory.py`, `memory_server.py`, `lite_memory.py`
