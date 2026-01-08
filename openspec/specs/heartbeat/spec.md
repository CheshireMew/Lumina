# heartbeat Specification

## Purpose
TBD - created by archiving change fix-heartbeat-proactive-chat. Update Purpose after archive.
## 需求
### 需求：多角色主动对话

HeartbeatService 必须在角色切换后正确跟踪新角色的空闲时间和主动对话阈值。

#### 场景：角色切换后的主动对话

- **给定** 用户从角色 A 切换到角色 B
- **当** HeartbeatService 重启
- **那么** 它应使用角色 B 的 `proactive_threshold_minutes` 配置
- **且** 空闲计时器应从切换时刻重新开始

---

### 需求：Inspiration API 使用知识图谱

主动对话的灵感数据必须从 SurrealDB 知识图谱获取，而非旧的 SQLite 数据库。

#### 场景：获取主动对话灵感

- **当** 调用 `/memory/inspiration` API
- **那么** 系统应从 SurrealDB 边表（如 LIKES, CONSIDERS 等）随机获取事实
- **且** 返回包含 `context`, `weight`, `emotion` 等字段的事实列表

