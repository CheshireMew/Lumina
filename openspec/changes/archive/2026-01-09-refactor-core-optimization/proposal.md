# Proposal: Core Optimization & Technical Debt Cleanup

## Summary
对 Python Backend 核心架构进行全面的技术债清理与优化。
本项目标不仅仅是为了 Lite 发行版打包,更是为了项目的长期健康度 (Project Health)。
核心行动包括 **移除已废弃的图谱代码**、**解耦上帝类 (God Class)**、**统一配置管理** 以及 **完善依赖治理**。

## 为什么 (Motivation)

1.  **代码腐烂 (Dead Code)**: 经过架构演进,复杂的"知识图谱 (Knowledge Graph)"功能已被废弃,但在 `surreal_memory.py` 中仍残留大量(~400行)相关代码 (`add_knowledge_graph`, `add_insights`),造成认知干扰和维护负担。
2.  **上帝类 (God Class)**: `surreal_memory.py` 承担了过多的职责(DB连接、向量检索、队列管理、旧图谱逻辑),违反单一职责原则 (SRP),难以测试和修改。
3.  **配置混乱 (Config Sprawl)**: 配置分散在多个 JSON 文件和环境变量中,缺乏统一管理的中心,系统行为难以预测。
4.  **环境脆弱 (Fragile Setup)**: `requirements.txt` 严重缺失核心依赖,使得新开发者或 CI 环境难以构建项目。

## 变更内容 (Proposed Changes)

### 1. 清理死代码 (Dead Code Removal)
- **移除** `surreal_memory.py` 中的 `add_knowledge_graph`, `add_insights` 及相关辅助函数 (`_resolve_entity`)。
- **清理** 数据库 Schema 初始化逻辑中不再使用的图谱相关 Table 定义。
- **确认** 不影响现有的 Vector Search (HNSW) 和 Episodic Memory 功能。

### 2. 重构 Memory 系统
将臃肿的 `SurrealMemory` 拆分为职责单一的组件:
- `memory/core.py`: 新版 `SurrealMemory` 主类(Facade)。
- `memory/vector_store.py`: 专注于 `episodic_memory` 的向量检索与存储。
- `memory/connection.py`: 健壮的 DB 连接池管理。
- **目标**: 将 `surreal_memory.py` 瘦身 50% 以上。

### 3. 统一配置中心 (`python_backend/app_config.py`)
- 扩展 `app_config.py`,实现 `ConfigManager`。
- 统一加载 `memory_config.json`, `stt_config.json` 等配置。
- 提供类型安全的配置访问接口。

### 4. 依赖治理
- 彻底扫描项目引用,补全 `requirements.txt`。
- 区分生产依赖与开发依赖。

## 风险 (Risks)
- **Schema Compatibility**: 移除代码时需确保不会意外删除生产环境中即使用户不使用的旧数据表(保持数据,仅移除应用层访问逻辑)。

## 验证计划
- 运行测试用例 `test/test_soul_evo_deepseek.py`,确保核心记忆流程(提取、整合、演化)不受影响。
- 手动验证 Backend 启动无报错。
