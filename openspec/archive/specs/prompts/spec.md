# 提示词优化规范 (Prompt Optimization Spec)

## 新增需求

### 需求:PromptManager 架构

系统必须提供一个统一的提示词管理模块,用于从外部文件加载和渲染提示词模板。

#### 场景:模板加载与渲染

- **功能**: 将提示词从 Python 代码中移出,存储为独立文件。
- **功能**: 支持从 `python_backend/prompts/` 递归加载模板。
- **功能**: 支持 Jinja2 风格的变量替换 `{{ variable }}`。
- **接口**:

```python
class PromptManager:
    def load(self, name: str) -> str: ...
    def render(self, name: str, context: dict) -> str: ...
```

## 修改需求

### 需求:对话提示词 (Chat Prompts)

系统生成的对话提示词(System Prompt 和 Dynamic Context)必须进行结构优化以节省 Token 并提高指令遵循度。

#### 场景:System Prompt (Static) 精简

- **原行为**: `SoulManager.render_static_prompt` 中硬编码大量否定指令。
- **新行为**: 使用 `prompts/chat/system.yaml` 模板。
- **内容优化**:

```yaml
role: |
  You are {{ char_name }}, not an AI.
  Core Traits: {{ traits }}.
style: |
  - Speak in {{ language }} with {{ mood }} tone.
  - Use short, spoken-style sentences.
  - Add emotional tags [emotion] at start.
constraints:
  - No moralizing or system-like disclaimers.
  - Assume previous context is known.
```

- **Token 目标**: 减少 20% 消耗。

#### 场景:Dynamic Context (Turn-Level) 压缩

- **原行为**: `SoulManager.render_dynamic_instruction` 生成长自然语言描述。
- **新行为**: 使用 `prompts/chat/context.yaml` 生成紧凑键值对。
- **示例**:

```text
[State]
Time: {{ time }}
Mood: {{ mood }} ({{ energy }}%)
Rel: {{ rel_label }} (Lv.{{ level }})
Instr: {{ instruction }}
```

### 需求:记忆提示词 (Memory Prompts)

记忆处理模块的提示词必须使用 One-Shot 示例和清晰的格式说明,以替代冗长的自然语言指令。

#### 场景:Extraction 任务优化

- **原行为**: `Dreaming._run_extractor` 使用大段文字解释 JSON。
- **新行为**: 使用 `prompts/memory/extract.yaml`,引入 One-Shot 示例代替说明。

#### 场景:Soul Evolution 思维链引导

- **原行为**: 直接要求 JSON 输出。
- **新行为**: 使用 `prompts/memory/evolve.yaml`,增加 CoT 引导步骤。

```

```
