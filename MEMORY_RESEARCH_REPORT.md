# 🧠 长期记忆方案深度调研报告

通过深入分析 `example` 目录下的几个开源项目，我们总结了三种截然不同的长期记忆实现方案。这些方案从轻量级到重量级各具特色，非常值得 Lumina 参考。

---

## 1. 识底深湖 (Deepseek Lunasia 2.0)
**方案代号**: `The Memory Lake` (文件湖 + 向量索引)
**核心文件**: `memory_lake.py`

### 🏗️ 架构设计
它没有使用重型数据库，而是发明了一种**基于文件系统的"记忆湖"**结构：
*   **存储层**: 将记忆存为独立的 JSON 文件，按 `Data/Timestamp` 命名，存放在文件夹中。
    *   例如: `chat_logs/memories/2024-01-01_12-00-00_UserTalksAboutAI.json`
*   **索引层**: 维护一个 `memory_index.json`，记录所有记忆的元数据（主题、时间、重要性）。
*   **检索层 (Dual Vectors)**: 
    *   **Topic Vector**: 对"记忆主题"（Summary）进行 Embedding。
    *   **Detail Vector**: 对"记忆详情"（Full Content）进行 Embedding。
    *   检索时同时匹配这两个向量。

### ✨ 亮点功能
*   **双重向量检索**: 既能搜到大意（Topic），也能搜到细节（Detail）。
*   **智能总结 Agent**: 有一个专门的 `MemorySummaryAgent`，每隔几轮对话就会总结当前话题，生成一个新的"记忆点"存入湖中。
*   **强制迁移机制**: 代码里包含详细的"数据迁移"逻辑，说明这种文件结构曾经历过迭代，维护了向后兼容性。

### ⚖️ 优缺点
*   **优点**: 极其直观，Debug 方便（直接看 JSON），无需维护 DB 进程。
*   **缺点**: 文件多了 IO 会变慢，不适合数万级记忆。

---

## 2. Live2D Virtual Girlfriend
**方案代号**: `Local Graph RAG` (本地轻量图谱)
**核心文件**: `src/graph_rag.py`

### 🏗️ 架构设计
这是一个非常惊艳的**"无数据库"图谱方案**。它不需要 Neo4j，而是直接用 Python 的 `networkx` 库在内存中构建图谱，并用 `pickle` 持久化到磁盘。

*   **实体与关系**: 
    *   使用 LLM 从对话中提取 `Entity` (实体) 和 `Relationship` (关系)。
    *   定义了工具函数 `tool_add_entity`, `tool_add_relationship` 供 LLM 调用。
    *   存储为 Graph Node 和 Edge (例如: `User -> like -> AI`).
*   **时间记忆 (Temporal Memory)**:
    *   **分层总结树**: 这是一个天才设计。
    *   它维护了一个 `Year -> Month -> Day` 的树状结构。
    *   每天结束总结成 Day Summary，每月结束总结成 Month Summary。
    *   检索时可以按时间维度进行"元数据过滤"。

### ✨ 亮点功能
*   **Hierarchical Summarization (分层总结)**: 自动把碎片对话聚合成高层记忆，模拟人类的长期记忆机制（模糊化旧细节，保留大意）。
*   **Lightweight Graph**: 用 `networkx` + `pickle` 实现了 Graph RAG 的所有好处，却没有任何运维成本。

### ⚖️ 优缺点
*   **优点**: 架构最优雅，兼顾了结构化（图谱）和时序性（分层树），且完全本地化。
*   **缺点**: `pickle` 文件如果损坏由于是二进制很难修复；随着图谱变大，加载速度可能受限。

---

## 3. NagaAgent
**方案代号**: `Heavy Graph RAG` (工业级图谱)
**核心文件**: `agent_memory.py`, `summer_memory`

### 🏗️ 架构设计
这是最"重"的方案，旨在构建一个完整的工业级 Agent。
*   **五元组提取**: 提取 `(Subject, Predicate, Object, Time, Location)`。
*   **后端存储**: 依赖外部的 **Neo4j** 图数据库。
*   **异步任务**: 使用 `AsyncTaskManager` 来后台处理记忆提取，不阻塞主聊天流程。

### ⚖️ 优缺点
*   **优点**: 查询能力最强，支持复杂的 Cypher 查询。
*   **缺点**: 部署太重，需要跑一个 Neo4j 实例，对个人助手来说有点杀鸡用牛刀。

---

## 4. MoeChat
**方案代号**: `YAML Editor` (以及潜在的 GraphRAG)
**核心文件**: `memory_editor_web.py`

### 🏗️ 架构设计
*   **核心记忆 (Core Memory)**: 一个单文件 `core_mem.yml`，定义最关键的设定（名字、性格）。
*   **长期记忆**: 文件夹里的 YAML 文件。
*   **人工干预**: 它提供了一个 Web 界面 (`MemoryEditor`)，允许用户**手动修改**记忆。这是一个很实用的功能，因为 AI 总会记错。

---

## 🏆 总结与 Lumina 推荐方案

| 特性 | Lunasia (Memory Lake) | Live2D (Local Graph) | NagaAgent (Neo4j) |
| :--- | :--- | :--- | :--- |
| **存储** | JSON Files | NetworkX + Pickle | Neo4j DB |
| **检索** | Dual Vector (Topic/Detail) | Graph + Time Tree | Graph Query |
| **复杂度** | ⭐⭐ | ⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| **适合场景**| 大量非结构化聊天记录 | 伴侣/助手 (强调关系和时间) | 企业级知识库 |

### 🚀 对 Lumina 的建议：**融合进化版 (LiteMemory)**

鉴于 `mem0` 的坑，以及上述调研，我建议 Lumina 采取 **Live2D + Lunasia** 的融合方案：

1.  **存储层 (借鉴 Lunasia)**: 使用 **JSON Lines (.jsonl)** 或 **JSON Files** 存储原始记忆。这比 Pickle 安全，比 DB 轻量。
2.  **索引层 (借鉴 Mem0/Lunasia)**: 使用 **Qdrant (Local)** 仅做向量索引。指向 JSON 文件的 ID。
3.  **逻辑层 (借鉴 Live2D)**:
    *   **时间分层**: 引入"每日总结"机制，把当天的对话压缩成 Summary 存入 Qdrant。
    *   **关系提取**: (可选) 在未来版本加入简单的 NetworkX 图谱，记录 User 和 Assistant 的关系变化。

**下一步行动**:
我们目前的 `simple_memory.py` (计划中) 将是这个方向的第一步：**完全掌控数据，使用本地文件 + Qdrant 索引**。
