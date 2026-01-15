# 变更:优化 LLM 提示词架构

## 为什么

当前系统中的 Prompt 分散在多个模块中(`SoulManager`, `Dreaming`),存在以下问题:

1.  **Token 浪费**:部分指令过于冗长,包含重复的否定句(如"不要...")和冗余的格式说明,增加了 API 调用成本。
2.  **性格表现不稳定**:核心的人格设定(Persona)与实时状态(State)混合在一起,容易导致模型在长对话中"忘记"核心设定或被实时指令覆盖。
3.  **维护困难**:提示词硬编码在 Python 代码中,非技术人员难以调整性格。

## 变更内容

本次变更将对系统中的所有 Prompt 进行深度审计、分类和优化。

### 1. 提示词功能分类与审计

我们识别出系统中的四类核心 Prompt:

| 类别                    | 所在模块                                        | 功能描述                                                           | 优化方向                                                                                |
| :---------------------- | :---------------------------------------------- | :----------------------------------------------------------------- | :-------------------------------------------------------------------------------------- |
| **核心设 (Persona)**    | `SoulManager.render_static_prompt`              | 定义"我是谁"、基本性格、说话风格。属于 Session 级静态上下文。      | **极致精简**:移除通用废话,强化核心性格关键词(Tag-based),利用 Context Caching。     |
| **动态状态 (State)**    | `SoulManager.render_dynamic_instruction`        | 注入当前心情、能量值、关系阶段、时间信息。属于 Turn 级动态上下文。 | **结构化数据**:从自然语言描述改为更紧凑的 `key: value` 或 JSON 片段,减少 Token 占用。 |
| **记忆处理 (Function)** | `Dreaming._run_extractor` / `_run_consolidator` | 执行特定 NLP 任务(提取数据、摘要)。                              | **Few-Shot + Schema**:使用少样本示例代替冗长说明,强制 JSON 格式。                     |
| **灵魂演化 (Meta)**     | `Dreaming._analyze_soul_evolution`              | 分析历史行为以更新性格参数。                                       | **思维链 (CoT)**:引导模型先分析后输出参数,提高参数更新的合理性。                      |

### 2. 具体的优化策略

- **English Instructions with Chinese Persona**: 实验证明,使用英文编写结构化指令(System Prompt)通常比中文更节省 Token 且逻辑遵循性更好,但保留中文的角色设定以确保说话味道原汁原味。
- **Positive Reinforcement**: 将"不要做 X"(Negative Constraints)改为"要做 Y"(Positive Instructions),模型遵循度更高。
- **XML/JSON Tagging**: 使用明确的 `<thought>`、`<reply>` 标签来引导模型输出,避免混淆思维链和回复。

### 3. 文件结构调整

- 将 Prompt 从 `.py` 文件中剥离,存放在 `python_backend/prompts/` 目录下的 `.yaml` 或 `.txt` 模板文件中,便于管理和热更新。

## 验证计划

- **Token 消耗对比**:在相同 Input 下,对比优化前后的 Token 消耗。
- **性格一致性测试**:使用 benchmark 问题集测试角色在不同情绪下的回复稳定性。
