# Lumina Memory Architecture V2.0 (LiteMemory)

> **版本**: 2.0.1
> **最后更新**: 2026-01-04
> **状态**: ✅ 已部署 / 生产就绪

Lumina V2 抛弃了不透明的 `mem0` 库,转而采用完全自研的 **LiteMemory** 架构。该架构专为"多角色扮演"和"长期伴侣"场景设计,核心在于**双层记忆隔离**与**自我维护机制**。

---

## 1. 核心架构设计

### 1.1 双层记忆模型 (Dual-Layer Memory)

我们将记忆分为两个物理隔离的层级,以解决"角色混淆"问题:

| 层级           | Collection 名称    | 用途                                                             | 示例                                              |
| :------------- | :----------------- | :--------------------------------------------------------------- | :------------------------------------------------ |
| **用户画像层** | `memory_user`      | 存储**关于用户**的客观事实。所有 AI 角色共享此数据。             | "用户叫 Dylan", "用户喜欢 Python", "用户住在上海" |
| **角色经历层** | `memory_{char_id}` | 存储**特定 AI 角色**与用户的共同经历和独有对话。各角色相互隔离。 | "Hiyori 和用户讨论过夏天", "AI 觉得用户很幽默"    |

### 1.2 短期记忆 (Short-Term Memory)

即**对话上下文窗口 (Context Window)**,Lumina 采用典型的混合存储策略:

- **位置**: 客户端/前端维护 (Client-Side State)。
- **机制**: **Sliding Window (滑动窗口)**。保留最近的 N 轮对话列表 (Direct Context),直接作为 Prompt 发送给 LLM。当轮次超过一定数量时,打包发送给 LLM 进行压缩。
- **作用**: 提供即时的、无损的对话连续性。
- **与长期记忆的交互**:
  - 长期记忆主要用于**检索 (RAG)**。
  - 在构建最终 Prompt 时,检索到的长期记忆事实会被注入到 `System Prompt` 中,作为"背景知识"支撑短期记忆窗口之外的信息。

### 1.3 数据流 (Data Pipeline)

当一条用户消息进入系统时,数据流向如下:

1.  **并行提取 (Parallel Extraction)**:
    - **通道 A (User Facts)**: `FactExtractor` 仅提取用户声明的客观信息 (Third-person)。
      - _Prompt 约束_: "禁止提取对话元数据", "保持原语言"。
    - **通道 B (Character Context)**: `LiteMemory` 提取对话主题、共同经历和 AI 的观点。
2.  **冲突检测 (Conflict Resolution)**:
    - 对新提取的事实进行向量检索 (Threshold 0.6)。
    - **LLM 分析**: 如果存在相似记忆,调用 DeepSeek 分析关系 (`ADD` / `REPLACE` / `MERGE` / `SKIP`)。
3.  **持久化 (Persistence)**:
    - **Qdrant**: 写入向量数据库 (用于检索)。
    - **JSONL Backup**:
      - 同步追加新事实到 `user_memory.jsonl` 或 `{char_id}_memory.jsonl`。
      - **关键机制**: 当发生 `MERGE` 或 `DELETE` 时,系统会同步重写 JSONL 文件,物理删除旧记录,防止文件无限膨胀。

---

## 2. 关键算法与策略

### 2.1 加权检索 (Weighted Retrieval)

为了解决"旧习惯"与"新偏好"的冲突(例如:以前喜欢红色,现在喜欢蓝色),我们在检索时引入了**时间衰减**:

$$ FinalScore = VectorScore \times (1.0 - DecayRate \times HoursElapsed) $$

- **DecayRate**: `0.0005` (每小时衰减 0.05%)。
- **效果**: 在语义相似度极高的情况下,更新鲜的记忆排名更高,从而"覆盖"旧记忆。

### 2.2 周期性整合 (Memory Consolidation)

为了保持数据库的精简,系统具备自我清洗能力:

- **触发条件**: 当某 Collection 的新增记录超过阈值 (如 10 条)。
- **执行逻辑**:
  1.  `MemoryConsolidator` 拉取所有相关记忆。
  2.  发送给 LLM 进行全局梳理、合并冗余项、消除矛盾。
  3.  **原子替换**: 删除旧的 N 条记录,插入 LLM 生成的 M 条精简记录 (M < N)。
  4.  **同步**: 调用 `_delete_from_disk` 清理物理备份文件。

### 2.3 多语言支持 (Multilingual)

- **Embedding 模型**: `paraphrase-multilingual-MiniLM-L12-v2`
- **维度**: 384
- **特性**: 真正支持跨语言检索。用户用中文提问可以匹配到英文记忆,反之亦然。

---

## 3. 文件与目录结构

```text
e:\Work\Code\Lumina\
├── python_backend/
│   ├── memory_server.py       # [API] FastAPI 服务入口,端口 8001
│   ├── lite_memory.py         # [Core] 核心逻辑:双层管理、加权检索、磁盘同步
│   ├── fact_extractor.py      # [Utils] 专门负责提取"用户画像"
│   ├── memory_consolidator.py # [Worker] 后台整合任务
│   └── rebuild_db.py          # [Tool] 数据库重建/迁移工具 (修复维度问题)
├── memory_backups/            # [Storage] 人类可读的持久化备份
│   ├── user_memory.jsonl      # 用户画像备份
│   └── hiyori_memory.jsonl    # 角色 Hiyori 的记忆备份
└── lite_memory_db/            # [DB] Qdrant 本地向量库文件 (自动生成)
```

## 4. 维护与故障排除

### 4.1 常见操作

- **启动服务**: `python python_backend/memory_server.py`
- **重建数据库**: 如果更换了 Embedding 模型或数据损坏,运行 `python python_backend/rebuild_db.py`。这将删除 DB 文件夹并从 JSONL 备份中恢复数据。

### 4.2 调试指南

- **数据重复**: 检查 `lite_memory.py` 中的 `_delete_from_disk` 是否被正确调用。
- **维度错误**: 确保 Qdrant Collection 的配置维度 (384) 与 Embedding 模型一致。
- **API 文档**: 访问 `http://localhost:8001/docs` 查看 Swagger UI。

---

> **设计哲学**:
>
> 1. **Keep It Simple**: 摒弃过度封装的库,直面底层数据。
> 2. **Everything on Disk**: 向量库只是索引,JSONL 才是唯一的真理来源 (SSOT)。
