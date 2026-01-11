### 需求：KV Cache Prefix Optimization

System Prompt 的构建必须遵循 DeepSeek 推荐的 Cache 策略：
`Static System Instruction` -> `Semi-Static Context` -> `Dynamic State`

#### 场景：Prompt 结构顺序

- **当** 构建 System Prompt 时
- **那么** 必须首先输出不需要频繁变更的静态信息（身份、特质、准则、数值）
- **且** 将关系背景、共同回忆等半静态内容作为中间层
- **且** 必须将高频变更的动态信息（心情、时间、精力、对方名字）放在 Prompt 的**最末尾**，确其不破坏前缀缓存

### 需求：Static/Dynamic 分离

必须将 System Prompt 拆分为“纯静态”和“动态指令”两个独立部分，以支持 Context Caching。

#### 场景：拆分渲染

- **当** 调用 `render_static_prompt` 时
- **那么** 仅返回身份、特质、数值、TTS 指令等静态内容
- **且** 不包含任何随时间或心情变化的描述

- **当** 调用 `render_dynamic_instruction` 时
- **那么** 返回心情、精力、时间、对方名字等动态内容

### 需求：保留原始数值

System Prompt 必须包含 Big Five 和 PAD 的原始浮点数值，供 AI 进行精确的角色扮演控制。

#### 场景：数值输出

- **当** 渲染 Big Five 或 PAD 信息时
- **那么** 必须输出原始 float 值（如 `openness: 0.85`）

### 需求：TTS 生成优化

System Prompt 必须包含指导 LLM 生成适合 TTS（文本转语音）阅读的文本的指令。

#### 场景：TTS 指令

- **当** 包含表达规范时
- **那么** 必须指示 LLM 使用情感标签 `[emotion]`
- **且** 必须指示 LLM 优化断句以获得自然的语音节奏
