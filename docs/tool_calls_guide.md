# DeepSeek Tool Calls & Strict Mode 实战指南

您提供的文档介绍了 **Tool Calls (工具调用)** 以及 DeepSeek 特有的 **Strict Mode (严格模式)**。这对于 Lumina 从一个“聊天机器人”进化为“全能 Agent”至关重要。

## 1. Tool Calls 是什么？

简单来说，就是**给 AI 装上“手”**。

- **没有 Tool Calls**：你问 AI “今天杭州天气怎么样？”，AI 只能瞎编（因为它的训练数据是截止到去年的）。
- **有 Tool Calls**：
  1.  你问同样的问题。
  2.  AI **并不直接回答**，而是返回一个数据包：`我要调用 get_weather(location="Hangzhou")`。
  3.  你的代码拦截到这个请求，去真的调天气 API，拿到 "24℃"。
  4.  你把 "24℃" 喂回给 AI。
  5.  AI 最终回答：“今天杭州 24℃，挺凉快的。”

## 2. 文档里的 "Strict Mode" (Beta) 是什么神器？

这是 DeepSeek 的杀手锏。

**痛点**：以前模型经常“乱填参数”。

- 比如你规定 `age` 必须是数字，它发神经给你填个 `"十八岁"`。
- 或者你规定 `mood` 只能是 `happy/sad`，它给你填个 `excited`。
- 导致你的程序这头 `json.loads` 直接报错崩溃。

**Strict Mode 解决方案**：

- 你在定义工具时，加上 `"strict": true`。
- **服务端**（DeepSeek）会帮你**强行校验**模型输出。
- **后果**：模型输出的 JSON **100% 符合你的 Schema 定义**。如果不符合，模型会被打回去重写，直到对为止。这对工程稳定性是**质的飞跃**。

---

## 3. 在 Lumina 中怎么用？(实战代码)

我们可以利用 Strict Mode 来重构 Lumina 的核心功能。

### 场景 A：绝对安全的性格/状态更新 (取代正则解析)

以前我们担心 LLM 输出的 JSON 格式不对，现在可以用 Strict Mode 完美控制。

```python
# 定义工具 Schema
update_state_tool = {
    "type": "function",
    "function": {
        "name": "update_lumina_state",
        "description": "当用户的行为对 Lumina 产生情感影响时调用此工具。",
        "strict": True,  # 开启严格模式！
        "parameters": {
            "type": "object",
            "properties": {
                "mood_shift": {
                    "type": "string",
                    "description": "心情变化方向",
                    "enum": ["happy", "sad", "angry", "neutral", "excited"] # 严格限制枚举
                },
                "intimacy_delta": {
                    "type": "integer",
                    "description": "好感度增减值 (-10 到 10)",
                    "minimum": -10,
                    "maximum": 10
                },
                "reason": {
                    "type": "string",
                    "description": "改变心情的原因 (用于日志)"
                }
            },
            "required": ["mood_shift", "intimacy_delta", "reason"], # 必须字段
            "additionalProperties": False
        }
    }
}

# 调用代码
response = client.chat.completions.create(
    model="deepseek-chat",
    messages=[...],
    tools=[update_state_tool]
)

# 处理逻辑
if response.choices[0].message.tool_calls:
    call = response.choices[0].message.tool_calls[0]
    args = json.loads(call.function.arguments)
    # 放心使用 args['mood_shift']，绝对不会是 "开心" 这种中文，一定是 "happy"
    soul_manager.update_mood(args['mood_shift'])
```

### 场景 B：精准的记忆归档

让 AI 帮我们提取记忆时，强制它输出结构化数据，而不是一段废话。

```python
archive_memory_tool = {
    "type": "function",
    "function": {
        "name": "save_memory",
        "strict": True,
        "parameters": {
            "type": "object",
            "properties": {
                "fact": {
                    "type": "string",
                    "description": "需要记住的事实，要简洁"
                },
                "category": {
                    "type": "string",
                    "enum": ["user_preference", "event", "task", "relationship"]
                },
                "importance_score": {
                    "type": "integer",
                    "minimum": 1,
                    "maximum": 5
                }
            },
            "required": ["fact", "category", "importance_score"],
            "additionalProperties": False
        }
    }
}
```

## 4. 总结：Strict Mode 对 Lumina 的意义

1.  **代码更少，更健壮**：不需要写一堆 `try-catch` 和 `if "happy" in response` 这种丑陋的解析代码了。
2.  **防止“胡言乱语”**：强制模型遵守 `enum` (枚举) 和 `pattern` (正则)，保证了系统内部数据的一致性。
3.  **开发体验**：把自然语言处理变成了**强类型编程**。

**结论**：强烈建议将 Lumina 中涉及“状态修改”、“记忆提取”的部分，全部升级为 **DeepSeek Strict Mode Tool Calls**。
