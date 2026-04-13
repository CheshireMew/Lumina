# ECA 自动化引擎 (Event-Condition-Action)

## 概述

ECA 引擎是 Lumina 的规则驱动行为系统，让角色能"主动"做事，而不仅仅是被动回复。

核心模式：**当 [事件发生] 且 [条件满足] 则 [执行动作]**

## 架构

```
EventBus / StateStore
      │
      ▼
  Trigger 匹配 ──► RuleEvaluator 检查 Conditions ──► 执行 Actions
```

### 文件结构

| 文件 | 职责 | 状态 |
|------|------|------|
| `models.py` | 数据模型 (Rule, Trigger, Condition, Action) | 完成 |
| `context.py` | StateStore (带 TTL 的 KV 存储 + 变更监听) | 完成 |
| `engine.py` | RuleEvaluator (无状态条件求值器) | 完成 |
| `service.py` | AutomationService (编排器) | 骨架完成，action 执行待实现 |

### 触发器类型

| 类型 | 说明 | 状态 |
|------|------|------|
| `event` | EventBus 事件触发 | 可用（自动订阅事件） |
| `state` | StateStore 值变化触发 | 可用 |
| `cron` | 定时触发 | 未实现 |
| `startup` | 系统启动触发 | 可用 |

### Action 类型

| 类型 | 说明 | 状态 |
|------|------|------|
| `log` | 打印日志 | 可用 |
| `emit_event` | 向 EventBus 发事件 | 骨架，未接通 |
| `proactive_chat` | 触发主动对话 | 骨架，未接通 |

## 典型用例

### 1. 主动聊天（idle 检测）
```python
Rule(
    id="proactive_idle",
    trigger=Trigger(type="state", value="user.state"),
    conditions=[
        Condition(key="user.state", comparator="==", value="idle"),
        Condition(key="system.last_interaction_delta", comparator=">", value=900)
    ],
    actions=[
        Action(type="proactive_chat", payload={"prompt": "idle"}),
    ],
    cooldown_seconds=300
)
```

### 2. 情感响应（配合 emotion_broker 插件）
```python
Rule(
    id="comfort_on_sad",
    trigger=Trigger(type="event", value="emotion:changed"),
    conditions=[
        Condition(key="current_emotion", comparator="==", value="sad")
    ],
    actions=[
        Action(type="proactive_chat", payload={"prompt": "comfort"})
    ],
    cooldown_seconds=60
)
```

### 3. 外部事件响应（MCP/Bilibili 弹幕）
```python
Rule(
    id="bilibili_danmaku",
    trigger=Trigger(type="event", value="mcp.bilibili.danmaku"),
    conditions=[],
    actions=[
        Action(type="proactive_chat", payload={"prompt": "react_to_danmaku"})
    ]
)
```

## 后续开发方向

### 必须完成
1. **`proactive_chat` action** — 调用 LLM 生成主动消息，通过 Gateway WebSocket 推送给前端
2. **`emit_event` action** — 构造 EventPacket 发到 EventBus
3. **StateStore 数据源接入** — 目前 StateStore 是空的，需要有人往里写数据：
   - `system.tick` 事件更新 `system.last_interaction_delta`
   - 前端 `/soul/interact` 调用重置 idle 计时器
   - emotion_broker 插件写入 `current_emotion`

### 可选扩展
- `cron` 触发器（基于 `asyncio` 定时循环）
- YAML 规则文件加载（`load_rules_from_yaml`）
- 规则热加载 / 前端规则编辑器
- 与前端 `useProactiveChat.ts` 合并（后端推送替代前端轮询）

## 与现有系统的关系

- **emotion_broker** 插件解析情感标签并广播事件 → ECA 可监听 `emotion:changed` 触发规则
- **useProactiveChat.ts** 前端轮询 `/soul` 检查 `pending_interaction` → 未来应由 ECA 后端推送替代
- **SoulService.set_pending_interaction()** 目前是空实现 → 应改为写入 StateStore，由 ECA 规则消费
