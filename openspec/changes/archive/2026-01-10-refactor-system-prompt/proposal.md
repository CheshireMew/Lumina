# Proposal: Refactor System Prompt for KV Cache Optimization

## Summary

重构 `SoulManager.render_system_prompt` 方法,优化 System Prompt 的结构以最大化利用 LLM KV Cache,并精简冗余内容。

## 为什么

1. **缓存失效**:当前 Prompt 将高度动态的"当前状态"(心情、精力)放在中间,导致后续所有静态指令的 KV Cache 失效,增加了推理延迟和 Tokens 消耗。
2. **冗余信息**:直接向 LLM 提供原始的 Big Five / PAD 数值(float)占用 Tokens 且效果不如描述性 Traits。
3. **表现力不足**:TTS 指令和关系演绎描述可以进一步优化。

## 变更内容

### 1. 架构设计: Minimal Static + Heavy Dynamic (Sandwich)

响应"动态提示词"的核心定义,我们将绝大部分状态移至动态区。

**Backend (`SoulManager`)**:

- `render_static_prompt()`: **极简前缀** (Identity Name, Basic Description, TTS Format). 仅保留绝对不变的基础设定。
- `render_dynamic_instruction()`: **完整动态状态** (Traits, Big Five/PAD Values, Mood, Energy, Relationship, Time).

**Frontend (`App.tsx`)**:

- 组装顺序:
  1. `[Static System Identity]` (Message[0], Cache Anchor)
  2. `[Conversation History]` (Append-only Context)
  3. `[Full Dynamic State]` (Last Message, Real-time Context)

此架构让 Traits 和数值也能随 Soul Evolution 实时生效,同时利用 Identity + History 的缓存。

## Compatibility

- **Non-Breaking**: 输出仍为 String,接口签名不变。
- **UI Impact**: 前端显示 System Prompt 时顺序会变化。
