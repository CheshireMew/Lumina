# Proposal: Implement Dreaming System (ReM)

## Summary

实现 **Recursive Episodic Memory (ReM)** “梦境系统”，替代原有的知识图谱架构。通过“回顾-重构”循环，将碎片化的对话日志转化为具备深度洞察的长期记忆。

## 为什么

1. **图谱局限性**: 原有的 Knowledge Graph (三元组) 提取成本高、检索僵硬，难以捕捉人类语言的微妙情感和潜台词。
2. **记忆割裂**: 旧记忆与新记忆缺乏融合机制，导致 AI 难以修正过时的认知。
3. **架构冗余**: 存在 `dreaming_legacy` 等旧代码与现有 `hippocampus` 功能重叠但逻辑冲突。

## 变更内容

### 1. 核心概念：记忆生命周期

记忆不再是静态的，而是流动的：

- **Raw (原始)**: 刚发生的对话日志。
- **Active (活跃)**: 经过“初次消化”，包含 `Summary` (摘要) 和 `Insight` (深层发散) 的记忆片段。
- **Pending Reconsolidation (待重构)**: 当一条 Active 记忆被检索命中 (Hit) 时，进入此状态。
- **Archived (归档)**: 被重构后的旧版本，不再参与检索，只做备份。

### 2. 核心循环 (The Loop)

- **Digestion (初次消化)**:
  - Input: 积累的 Raw Logs。
  - Process: LLM 提取摘要、时间锚点、情绪和深层洞察 (Insight)。
  - Output: Active Memory Fragments.
- **Dreaming (重构/做梦)**:
  - Input: 新的 Raw Logs + 标记为 Pending 的旧记忆。
  - Process: LLM 将新旧信息**融合**，解决冲突，深化感悟。
  - Output: 新的 Consolidated Memory (覆盖旧记忆)。

### 3. 组件变更

- **`surreal_memory.py`**:
  - Schema 升级：`memory` 表新增 `summary`, `insight`, `status`, `relevance_count` 字段。
  - 逻辑升级：`search()` 命中高分记忆时，异步将其标记为 `status='pending_reconsolidation'` (Touch-to-Dirt)。
- **`hippocampus.py`**:
  - **完全重写**。移除 Graph 提取逻辑。
  - 实现 `digest_raw_memories()` (Raw -> Active)。
  - 实现 `dream_cycle()` (Raw + Pending -> Consolidated)。
- **`heartbeat_service.py`**:
  - 接入 `Dreaming` 触发逻辑（空闲时触发重构）。

## Compatibility

- **Breaking Change**: 将移除所有 Knowledge Graph 相关代码和表 (`entity`, `relation`)。
- **Legacy**: 借鉴 `dreaming_legacy.py` 的循环结构和 `memory_consolidator_legacy.py` 的冲突检测思想。
