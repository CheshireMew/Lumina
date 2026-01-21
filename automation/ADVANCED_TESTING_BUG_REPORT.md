# 高阶测试阶段 - Bug 报告 (Advanced Testing Bug Report)

本报告汇总了在执行 E2E、压力、前端单元及混沌测试过程中发现的所有问题。

### [Critical] E2E 500 Error in Unified Chat Response

- **File**: `python_backend/routers/completions.py`
- **Cause**: Attempting to access `services.soul_client` (which does not exist) instead of `services.soul`.
- **Impact**: All E2E chat tests fail with Internal Server Error.
- **Evidence**: `AttributeError: 'ServiceContainer' object has no attribute 'soul_client'`
- **修复方案 (建议)**:
  - 将 `_get_soul_client` 中引用的 `services.soul_client` 修改为 `services.soul`。
  - 同步更新 `character_id` 的获取逻辑，如下所示：
    ```python
    character_id = getattr(soul_service, "_active_character_id", character_id)
    ```

### [Critical] Architectural Limitation: Single-Turn Tool Execution

- **File**: `python_backend/services/chat/pipeline.py`
- **Cause**: `LLMExecutionStep` hardcodes a single tool execution turn and then forces a final answer with `tools=None`.
- **Impact**: Multi-turn tool logic (where one tool's result triggers another tool call) is fundamentally broken.
- **Evidence**: Line 190 in `pipeline.py` explicitly disables tools during the second pass.

### [High] Frontend Race Condition in DataViewer

- **File**: `app/renderer/components/DataViewer/DataViewer.tsx`
- **Cause**: `loadTableData` lacks an `AbortController`. If `activeCharacterId` changes during a slow load, old data can overwrite new data.
- **Impact**: Data inconsistency in the management UI.

### [Medium] Missing Virtualization in DataViewer

- **File**: `app/renderer/components/DataViewer/TableSection.tsx`
- **Cause**: Uses standard `<table>` mapping without virtualization (e.g., `react-window`).
- **Impact**: Significant UI lag when rendering thousands of records (currently partially masked by a hardcoded `limit=50`).
- **Evidence**: Direct `tableData.map()` usage on line 137.

### [Minor] Chaos Test Failure: File Descriptor Exhaustion

- **Test**: `test_file_descriptor_exhaustion` in `automation/tests_pytest/chaos/test_chaos.py`
- **Issue**: OS-level limits reached during test; infrastructure-dependent but highlights need for better resource pooling.
- **原因**: 每个环境的文件描述符限制不同，测试用例中的 100 个文件可能不足以触发限制，或者清理逻辑与 Windows 句柄释放机制存在时间差。
- **建议**: 针对 Windows 平台调整测试阈值，或将其标记为资源依赖型测试。

## 3. 性能测试发现 (Optimization)

- **发现**: 在 200 个并发异步任务下，系统响应时间保持在 1s 以内。
- **瓶颈预测**: 虽然异步 I/O 表现优异，但如果插件逻辑涉及重度 CPU 计算（如模型推理），在高并发下仍可能因 GIL 导致延迟增加。

## 4. 前端测试覆盖 (Info)

- **现状**: 已成功覆盖 `DataViewer` 的基础渲染逻辑。

## 5. 深度后端硬化测试 (Deep Backend Hardening)

### [PASS] 并发竞态验证 (Concurrency Race)

- **File**: `automation/tests_pytest/backend/test_concurrency_race.py`
- **Result**: 30 个并发插件状态切换请求全部成功，未发现数据库竞态问题。
- **Evidence**: `Success: 30, Errors: 0`

### [BLOCKED] 状态损坏鲁棒性 (State Corruption)

- **File**: `automation/tests_pytest/backend/test_state_robustness.py`
- **Cause**: 测试脚本无法直连 PostgreSQL，`asyncpg` 连接反复报错 `connection was closed in the middle of operation`。
- **Impact**: 无法验证后端对损坏 JSON 的容错性。
- **Root Cause (Suspected)**: `app_config.py` 中配置的凭据 (`lumina_user`/`lumina_password`) 与实际 PostgreSQL 实例不匹配。后端服务运行成功说明存在环境特殊配置（如 PgBouncer）。

### [BLOCKED] 分布式同步压力 (Sync Churn)

- **File**: `automation/tests_pytest/backend/test_sync_churn.py`
- **Cause**: 同上，依赖直连数据库的测试路径均被阻塞。

### [PASS] 僵尸进程清理 (Orphan Cleanup)

- **File**: `automation/tests_pytest/infra/test_process_cleanup.py`
- **Result**: 使用动态端口启动 STT Worker，强行 kill 后端口正常释放，未检测到僵尸进程。
- **Note**: 当前测试使用 `LUMINA_STT_PORT` 环境变量覆盖端口，但 `app_config.py` 是否支持该变量未经确认。

---

_注：按照指令，以上 Bug 仅在此报告中记录，未对生产代码进行修改。_
