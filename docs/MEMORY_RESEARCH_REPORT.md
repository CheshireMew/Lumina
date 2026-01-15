# 记忆数据库选型对比与架构方案

## 1. 深度对比 (按您的要求逐个分析)

目标:寻找 **"Native Multi-model" (原生多模态)** + **"All-in-One" (不乱)** + **"Embedded" (适合桌面应用)** 的最佳方案。

### 数据库类 (Databases)

| 候选者          | 原生多模态                                                            | 向量能力                                        | 嵌入式/本地化                                                   | 多角色支持                                           | 评价                                                                |
| :-------------- | :-------------------------------------------------------------------- | :---------------------------------------------- | :-------------------------------------------------------------- | :--------------------------------------------------- | :------------------------------------------------------------------ |
| **SurrealDB**   | ⭐⭐⭐⭐⭐<br>Graph + Doc + Vector 完美融合,同一个引擎处理所有数据。 | **Native**<br>内置 HNSW 索引,语法原生支持。    | ⭐⭐⭐⭐⭐<br>**单文件二进制**或嵌入式库,零依赖,最干净。      | **优**<br>通过图边 (Edges) 或 NS/DB 隔离,非常灵活。 | **👑 最佳选择**<br>唯一真正满足"原生多模态"且"嵌入式"的现代数据库。 |
| **ArangoDB**    | ⭐⭐⭐⭐<br>老牌多模态 (Graph + Doc),功能强大。                      | **Plugin**<br>依赖 FAISS 集成,非完全原生体验。 | ⭐⭐<br>通常作为**服务**运行 (Docker/Service),对桌面应用太重。 | **优**<br>多租户 (Tenancy) 支持好。                  | **太重**<br>部署和维护成本高,不适合本地单机 App。                  |
| **Neo4j**       | ⭐⭐⭐<br>Graph First。虽然加了向量,但核心还是图。                   | **Native**<br>近期添加了向量索引。              | ⭐<br>Java 编写,内存占用大,依赖 JVM,部署最"乱"。             | **良**<br>基于标签 (Label) 隔离。                    | **太乱**<br>引入 Java 环境对 Python 项目是灾难。                    |
| **Memgraph**    | ⭐⭐⭐<br>Graph First (内存数据库)。                                  | **Native**<br>基于 C++ 的高性能向量搜索。       | ⭐⭐⭐<br>有 Docker 镜像,但不如单文件方便。                    | **良**<br>图隔离。                                   | **偏科**<br>侧重高性能图算法,文档存储能力弱于 Surreal。            |
| **NebulaGraph** | ⭐⭐⭐<br>针对海量数据的分布式图数据库。                              | **Native**<br>支持向量。                        | ⭐<br>分布式架构,完全不适合单机桌面应用。                      | **良**<br>Space 隔离。                               | **杀鸡用牛刀**<br>架构太复杂。                                      |

### 框架类 (Frameworks) - 它们不是数据库,而是"用法"

| 候选者        | 定位           | 特点                                              | 适用性                                                    |
| :------------ | :------------- | :------------------------------------------------ | :-------------------------------------------------------- |
| **LightRAG**  | RAG 框架       | 强调"轻量级",通常配合 NetworkX (本地) 或 Neo4j。 | **可借鉴思想**,但不解决存储选型。                        |
| **Graphiti**  | 知识图谱库     | 专注动态时序图谱。                                | 依赖 Neo4j/FalkorDB,**不是独立数据库**。                 |
| **Cognee**    | 记忆引擎       | 旨在连接由于图和向量。                            | 也是上层框架,底层还要选数据库。                          |
| **LangGraph** | **Agent 编排** | 定义 Agent 的思考流程 (State Machine)。           | **必须用**,但它是逻辑层,和存储层 (SurrealDB) 配合使用。 |

---

## 2. 为什么 SurrealDB 是多角色 AI 的绝配?

结合您的研究文档 `AI性格培养:记忆数据驱动.txt`,我们需要一个能同时通过 **"感性 (向量)"** 和 **"理性 (图谱/事实)"** 来塑造性格的系统。

**多角色场景 (Lillian vs Hiyori)** 在 SurrealDB 中的实现:

### 结构设计

我们不需要建立多个数据库,只需利用 **Graph 的边 (Edge)** 来自然隔离和关联。

```sql
-- 1. 定义实体
CREATE character:lillian;
CREATE character:hiyori;
CREATE user:dylan;

-- 2. 存储事实 (同时是 Document 和 Vector)
-- 这是一条"感性记忆",带有向量和情感标签
CREATE fact:f1 SET
    text = "User likes cyberpunk style",
    embedding = [...],
    emotion = "excited",
    time = time::now();

-- 3. 建立关系 (Graph) - 这一步实现了"隔离"与"性格"
-- Lillian 观察到了这个事实,并产生了"崇拜"的情绪链接
RELATE character:lillian->observes->fact:f1 SET weight=0.9, feeling="admire";

-- Hiyori 也观察到了同一个事实,但产生了"怀疑"的情绪链接
RELATE character:hiyori->observes->fact:f1 SET weight=0.5, feeling="skeptical";
```

### 检索策略 (All-in-One 查询)

当 Lillian 需要说话时,我们执行一条 SurrealQL 查询,就能获取 **"符合 Lillian 性格 + 语义相关 + 逻辑正确"** 的上下文:

```sql
SELECT
    ->observes->fact.text AS memory,
    ->observes.feeling AS my_feeling,  -- 获取 Lillian 独有的情感视角
    vector::similarity::cosine(->observes->fact.embedding, $current_context) AS relevance
FROM character:lillian
WHERE ->observes->fact.time > time::now() - 30d  -- 时间衰减
ORDER BY relevance DESC
LIMIT 5;
```

**结论**:Hiyori 的查询完全一样,只是把主体换成 `character:hiyori`,她就会得到属于她的、带有她情感色彩的记忆。这就是 **Native Multi-model** 的威力——**数据共享,视角隔离**。

---

## 3. 最终架构建议

**底层存储**: **SurrealDB** (单文件嵌入式运行)

- 负责:向量存储、知识图谱、文档记录、多角色隔离。

**逻辑编排**: **LangChain / LangGraph** (Python 代码)

- 负责:对话流控制、Prompt 组装、工具调用。

**记忆算法**: 参考 **LightRAG** 的双层检索思想

- 1. **Local Search**: 在 SurrealDB 中搜具体的 Entity 和 Fact。
- 2. **Global Search**: 在 SurrealDB 中遍历图谱关系 (User -> prefers -> Style)。

这个方案最干净、最先进,且完全符合您对多角色和性格培养的深度需求。

---

## 4. 下一步计划

1.  **废弃 Qdrant 和 SQLite**。
2.  **部署 SurrealDB** (下载 windows 单文件 `surreal.exe`)。
3.  **重写 LiteMemory** 适配 SurrealQL。
4.  **迁移数据**。
