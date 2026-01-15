# 任务清单

- [ ] **提示词工程基础建设**

  - [ ] 创建 `python_backend/prompts/` 目录结构
  - [ ] 实现 `PromptManager` 类,支持加载 YAML/TXT 模板和变量注入
  - [ ] 在 `AppConfig` 中添加 Prompt 相关配置(如模板路径)

- [ ] **Persona (Chat) 提示词优化**

  - [ ] 提取并重构 `static_prompt` (Identity) 为 `prompts/chat/system.yaml`
    - [ ] 移除冗余否定指令
    - [ ] 优化情感标签说明
  - [ ] 提取并重构 `dynamic_instruction` (State) 为 `prompts/chat/context.yaml`
    - [ ] 压缩 Context 数据格式 (Compact Key-Value)
  - [ ] 更新 `SoulManager` 使用新模板

- [ ] **Memory (Dreaming) 提示词优化**

  - [ ] 提取 `extractor` 提示词至 `prompts/memory/extract.yaml`
    - [ ] 添加 One-Shot 示例
    - [ ] 简化任务描述
  - [ ] 提取 `consolidator` 提示词至 `prompts/memory/consolidate.yaml`
  - [ ] 提取 `soul_evolution` 提示词至 `prompts/memory/evolve.yaml`
  - [ ] 更新 `Dreaming` 类使用新模板

- [ ] **验证与测试**
  - [ ] 运行 `test/test_prompts.py` (需创建) 验证模板渲染正确性
  - [ ] 人工验证对话回复的性格表现
