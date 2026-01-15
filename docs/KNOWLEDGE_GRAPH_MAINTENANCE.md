# Lumina 知识图谱维护架构文档

## 1. 概述与核心理念

本文档概述了在 SurrealDB 中维护 Lumina 知识图谱 (KG) 的长期健康度、一致性和可用性的工程策略。

**核心理念:**

1.  **AI 优先治理 (AI-First Curation)**:利用 LLM 处理复杂的实体消歧,而不是依赖严格的数据库 Schema。
2.  **概率性记忆 (Probabilistic Memory)**:知识不是静态的,它拥有"强度"。除非被反复强化,否则会随时间衰减(遵循艾宾浩斯遗忘曲线)。
3.  **轻量化工程 (Lightweight Engineering)**:避免引入沉重的企业级图数据库工具(如基于 Java 的 JanusGraph),充分利用 SurrealDB 原生的多模态能力。
4.  **All-in-One 数据层**:使用 SurrealDB 统一存储向量、文档和图谱边,简化技术栈。

---

## 2. 架构及其数据与维护的分离

我们将"经历 (Experience)"与"知识 (Knowledge)"区分开来。

| 组件                           | 存储类型                           | 用途                              | 维护策略                                             |
| :----------------------------- | :--------------------------------- | :-------------------------------- | :--------------------------------------------------- |
| **情景记忆 (Episodic Memory)** | `TABLE conversation`               | 存储原始对话历史日志。            | **不可变日志**。通过向量搜索 + 全文搜索进行检索。    |
| **语义记忆 (Semantic Memory)** | `TABLE entity`, `TABLE <relation>` | 存储提取的事实 (A -> 关系 -> B)。 | **需要主动维护**。包括实体消歧、冲突解决、自然遗忘。 |

---

## 3. 维护策略阶段

### Phase 1: 摄入与去重(守门人机制)

**目标**:在源头防止图谱被污染。例如,识别出 "Apple" 和 "苹果" 是同一个实体。

#### 1.1 基于向量的实体消歧(实时)

在创建新实体之前,必须检查语义上是否已存在重复项。

- **逻辑**:

  1.  为新候选实体名称生成 Embedding 向量。
  2.  查询 `entity` 表,寻找余弦相似度 `cosine_similarity > 0.92`(可配置)的现有实体。
  3.  **若匹配**:复用现有实体的 ID。
  4.  **若无匹配**:创建新实体 ID。

- **代码设计 (`surreal_memory.py`)**:
  ```python
  async def _resolve_entity(self, raw_name: str) -> str:
      # 1. Encode raw_name (编码名称)
      # 2. SELECT id FROM entity WHERE embedding <|0.92|> $new_emb LIMIT 1 (向量搜索)
      # 3. UPSERT or RETURN existing (返回现有ID或创建新ID)
  ```

#### 1.2 边的强化(肌肉模型)

边(关系)不是非黑即白的(存在或不存在),它们具有权重/强度。

- **Schema 扩充**:

  - `base_strength` (浮点数, 0.0-1.0):提取时的初始置信度。
  - `reinforcement_count` (整数):该事实被提及的次数。
  - `last_mentioned` (时间戳):最后一次被强化的时间。
  - `decay_rate` (浮点数):默认 0.01/天(衰减率)。

- **Upsert 逻辑**:
  - **新边**:`base_strength = 0.8`, `count = 1`。
  - **现有-边**:`base_strength = min(1.0, current + 0.1)`, `count += 1`, `last_mentioned = now()`。

---

## 4. 维护策略:生命周期管理

### Phase 2: 生物性遗忘(垃圾回收机制)

**目标**:模拟人类的遗忘机制。不重要或错误的事实会自然淡出。
**实现方式**:动态查询过滤(读时过滤)。

我们不立即物理删除边,而是根据计算出的"有效强度"进行过滤:

$$ \text{当前强度} = \text{基础强度} \times (1 - \text{衰减率})^{\Delta t} $$

- **检索查询示例**:
  ```sql
  SELECT
      ->? as relation,
      (base_strength * math::pow(0.99, duration::days(time::now() - last_mentioned))) as effective_strength
  FROM entity:Hiyori
  WHERE effective_strength > 0.1 -- 过滤掉已"遗忘"的微弱记忆
  ```

### Phase 3: 周期性治理(园丁机制)

**目标**:修复自动化消歧遗漏的语义冲突。
**机制**:由 `HeartbeatService` 触发每周运行的 `GraphCurator` 任务。

#### 3.1 冲突检测

识别逻辑矛盾(通过规则或 LLM Prompt 定义)。

- _示例_:存在 `Hiyori -> LIKES -> Apple` 同时存在 `Hiyori -> HATES -> Apple`。
- _动作_:比较 `effective_strength`(有效强度)。如果差异很大,删除弱的一方。如果差异很小,询问用户或将两者标记为"冲突 (Conflicted)"。

#### 3.2 聚类与社区检测(未来规划)

借鉴 **Microsoft GraphRAG** 的逻辑。

1.  导出图谱子集。
2.  运行 Leiden 聚类算法。
3.  生成"社区摘要"(例如,"这个聚类代表用户对加密货币投资的兴趣")。
4.  将摘要回写到 `TABLE insight`。

---

## 5. SurrealDB 特性专项优化

利用 SurrealDB 的独特功能来降低代码复杂度。

| 特性               | 在 Lumina 中的应用                                                                                       |
| :----------------- | :------------------------------------------------------------------------------------------------------- |
| **`DEFINE EVENT`** | **自动反向边**:当创建 `A->LIKES->B` 时,自动触发创建 `B->LIKED_BY->A`,以便更快速地进行反向查询。       |
| **`CHANGEFEED`**   | **审计日志**:在 `entity` 和 `relation` 表上开启 Changefeed,追踪知识随时间的演变(支持时光倒流/回滚)。 |
| **`LIVE SELECT`**  | **实时 UI**:当 `Hippocampus` 提取出新事实时,立即将图谱更新推送到前端 `SurrealViewer`。                 |

---

## 6. 推荐技术栈

1.  **核心数据库**:**SurrealDB** (保持不变,完美契合 All-in-One 需求)。
2.  **Embedding 模型**:`all-MiniLM-L6-v2` (本地运行,速度快),用于实体消歧。
3.  **治理逻辑 (Curator)**:**Python 脚本** (由 `HeartbeatService` 调度)。
4.  **可视化**:**SurrealViewer** (React + Cytoscape/D3)。

## 7. 立即执行的下一步(行动计划)

1.  **修改 `surreal_memory.py`**:
    - 实现 `_resolve_entity` 方法,使用向量相似度匹配。
    - 更新 `add_knowledge_graph` 以使用消歧后的 ID。
2.  **Schema 迁移**:
    - 在创建边的逻辑中添加 `strength`(强度)相关字段。
3.  **可视化更新**:
    - 更新 `search_hybrid` 以支持 `effective_strength`(包含时间衰减因素)。

---

_Created by Antigravity Agents for Lumina Project_
