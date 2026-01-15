# dreaming Specification

## Purpose
TBD - created by archiving change implement-dreaming-system. Update Purpose after archive.
## 需求
### 需求:Extractor (初步提取)

- **触发**: 系统必须在即使有少量新对话 (e.g. 5 条) 或每隔短时间 (e.g. 1 分钟) 时触发。
- **输入**: `conversation_log` 中 `is_processed=False` 的记录。
- **处理**: LLM 必须分析对话,提取 N 个独立的记忆点。
- **输出**:
  1. 写入 `episodic_memory` (Status='active').
  2. 标记 `conversation_log` 为 `is_processed=True`.

#### 场景:Extractor 触发

- **当** 累积 5 条新对话
- **那么** 提取记忆并存入 active

### 需求:Consolidator (递归重构)

- **触发**: 系统必须在系统空闲 (Idle) 或 Pending 队列堆积时触发。
- **输入**: `episodic_memory` 中 `status='pending_reconsolidation'` 的记录。
- **处理**:
  1. 检索与 Pending 记忆向量相似的其他 Active 记忆 (Context)。
  2. LLM 必须综合 Pending + Context。
  3. 决策:合并 (Merge), 拆分 (Split), 删除 (Delete), 或 更新 (Update)。
- **输出**: 执行 LLM 的增删改指令,维护 `episodic_memory` 表的整洁。

#### 场景:Consolidator 触发

- **当** 累积 20 条高频 Pending 记忆
- **那么** 触发重构

