# Spec: Soul API Bulk Operations

## 新增需求

### 需求:Bulk User Name Update

系统 **必须 (MUST)** 提供一种高效的机制,以便在用户修改全局设置(如用户名)时,能够一次性更新所有角色的持久化状态,而无需前端发起多次请求。

#### 场景:批量更新用户名

**Given** 当系统中有多个角色(例如:Hiyori, Amadeus, Kurisu),且用户在设置中修改了"User Name"
**When** 用户点击保存 Settings
**Then** 系统应通过单个 API 请求 (`POST /soul/user_name_bulk`) 同时更新所有角色的 `relationship.user_name` 字段
**And** 不应产生 N 次独立的 HTTP 请求
**And** 更新后所有角色的持久化文件 (`state.json`) 应反映新的用户名
