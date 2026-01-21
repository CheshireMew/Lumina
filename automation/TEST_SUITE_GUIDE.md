# Lumina 专业测试套件完整指南

## 测试基础设施概览

```
automation/
├── conftest.py                          # Pytest 配置和共享 fixtures
├── pytest.ini                           # Pytest 配置文件
├── run_pytest_with_coverage.py          # 带覆盖率的测试运行器
├── run_all_tests.py                     # Unittest 运行器（兼容性）
├── PYTEST_MIGRATION_GUIDE.md          # 迁移指南
│
├── fixtures/                            # 可重用测试组件
│   ├── __init__.py
│   ├── factories.py                     # 测试数据工厂
│   ├── data_generators.py              # 随机数据生成器
│   └── mock_servers.py                  # Mock HTTP 服务器
│
├── tests/                               # 现有 unittest 测试
│   ├── backend/
│   ├── core/
│   ├── infra/
│   ├── plugins/
│   └── services/
│
└── tests_pytest/                        # 新的 pytest 测试
    ├── test_container_pytest.py         # 基础 pytest 示例
    ├── test_chat_parametrized.py        # 参数化测试
    ├── test_with_fixtures.py             # Fixture 使用示例
    ├── test_property_based.py           # 属性测试
    ├── test_data_driven.py              # 数据驱动测试
    │
    ├── performance/                      # 性能测试
    │   └── test_benchmarks.py
    │
    ├── security/                         # 安全测试
    │   ├── test_security_checks.py    # 安全检查测试
    │   └── test_scan.py                 # 自动化安全扫描
    │
    ├── e2e/                             # 端到端测试
    │   └── test_chat_scenarios.py
    │
    ├── chaos/                            # 混沌测试
    │   └── test_chaos.py                # 故障注入测试
    │
    ├── load/                             # 负载测试
    │   └── test_load.py                 # 并发负载测试
    │
    └── memory/                           # 内存测试
        └── test_memory_leaks.py          # 内存泄漏检测
```

---

## 快速开始

### 安装依赖

```bash
# 核心测试框架
pip install pytest pytest-asyncio pytest-cov

# 可选：高级测试工具
pip install pytest-benchmark hypothesis

# 可选：HTTP 测试
pip install httpx aiohttp
```

### 运行测试

```bash
# 运行所有 pytest 测试
cd automation
pytest tests_pytest/ -v

# 运行带覆盖率的测试
python run_pytest_with_coverage.py

# 运行特定类型的测试
pytest -m unit -v              # 只运行单元测试
pytest -m security -v           # 只运行安全测试
pytest -m performance -v        # 只运行性能测试

# 运行特定文件
pytest tests_pytest/test_container_pytest.py -v

# 查看可用 fixtures
pytest --fixtures
```

---

## 测试类型详解

### 1. 单元测试 (Unit Tests)

**位置**: `tests_pytest/test_container_pytest.py`

**目的**: 测试单个函数/类/方法

**特点**:
- 快速（毫秒级）
- 无外部依赖
- 使用 mock 隔离

**示例**:
```python
def test_singleton_pattern():
    ServiceContainer._instance = None
    instance1 = ServiceContainer.get_instance()
    instance2 = ServiceContainer.get_instance()
    assert instance1 is instance2
```

### 2. 参数化测试 (Parametrized Tests)

**位置**: `tests_pytest/test_chat_parametrized.py`

**目的**: 用多个输入测试同一逻辑

**特点**:
- 一个测试定义 = 多个测试用例
- 自动生成描述性测试名称
- 减少重复代码

**示例**:
```python
@pytest.mark.parametrize("input,expected", [
    ("hello", "greeting"),
    ("weather", "query"),
])
def test_intent_detection(input, expected):
    assert detect_intent(input) == expected
```

### 3. 性能测试 (Performance Tests)

**位置**: `tests_pytest/performance/test_benchmarks.py`

**目的**: 确保代码性能满足要求

**特点**:
- 基准测试
- 内存使用检查
- 并发测试
- 扩展性测试

**运行**:
```bash
# 需要安装 pytest-benchmark
pip install pytest-benchmark
pytest tests_pytest/performance/ -v --benchmark-only
```

### 4. 安全测试 (Security Tests)

**位置**: `tests_pytest/security/test_security_checks.py`

**目的**: 发现安全漏洞

**测试内容**:
- SQL 注入防护
- XSS 防护
- 路径遍历防护
- 输入验证
- 权限检查

**示例**:
```python
@pytest.mark.parametrize("malicious_input,attack_type", [
    ("'; DROP TABLE users; --", "SQL Injection"),
    ("<script>alert('xss')</script>", "XSS"),
])
def test_malicious_input_detection(malicious_input, attack_type):
    threat = detect_threat(malicious_input)
    assert threat is not None
```

### 5. 端到端测试 (E2E Tests)

**位置**: `tests_pytest/e2e/test_chat_scenarios.py`

**目的**: 测试完整用户场景

**特点**:
- 真实 HTTP 请求
- 需要服务运行
- 测试用户工作流

**运行前准备**:
```bash
# 启动服务
npm run dev

# 运行 E2E 测试
pytest tests_pytest/e2e/ -v
```

### 6. 数据驱动测试 (Data-Driven Tests)

**位置**: `tests_pytest/test_data_driven.py`

**目的**: 从外部文件加载测试数据

**特点**:
- 测试数据在 YAML/JSON 文件
- 易于维护
- 非程序员可更新测试用例

---

## Fixture 系统详解

### 内置 Fixtures (conftest.py)

| Fixture | 用途 |
|---------|------|
| `mock_container` | 预配置的 ServiceContainer mock |
| `mock_llm_manager` | Mock LLM 管理器 |
| `mock_soul_service` | Mock Soul 服务 |
| `async_http_client` | 异步 HTTP 客户端 |
| `service_urls` | 服务端点 URL |
| `chat_message_factory` | 创建聊天消息 |
| `memory_factory` | 创建内存数据 |

### 使用示例

```python
def test_with_fixtures(mock_container, mock_llm_manager):
    # Fixtures 自动注入，无需初始化
    mock_container.set_llm_manager(mock_llm_manager)
    result = mock_container.get_llm_manager()
    assert result is mock_llm_manager
```

---

## 标记 (Marks) 系统

### 可用标记

```python
@pytest.mark.unit              # 单元测试
@pytest.mark.integration       # 集成测试
@pytest.mark.e2e               # 端到端测试
@pytest.mark.slow              # 慢速测试
@pytest.mark.security          # 安全测试
@pytest.mark.performance       # 性能测试
```

### 运行标记的测试

```bash
pytest -m unit              # 只运行单元测试
pytest -m "not slow"         # 排除慢速测试
pytest -m "security or e2e"  # 组合标记
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 终端输出
pytest --cov=python_backend --cov-report=term-missing

# HTML 报告
pytest --cov=python_backend --cov-report=html

# 使用脚本
python run_pytest_with_coverage.py --html
```

### 查看报告

```bash
# HTML 报告位置
start automation/htmlcov/index.html

# 报告包含：
# - 行覆盖率
# - 分支覆盖率
# - 未覆盖的代码行（高亮显示）
```

---

## 最佳实践

### 1. 测试命名

```python
# 好的命名
def test_user_login_with_valid_credentials_succeeds():
    pass

# 不好的命名
def test_login():
    pass
```

### 2. 一个测试一件事

```python
# 好的测试
def test_login_returns_token_on_success():
    pass

def test_login_raises_error_on_invalid_credentials():
    pass

# 不好的测试
def test_login():
    # 测试了太多事情
    pass
```

### 3. 使用 Fixtures 复用代码

```python
# 好的 - 使用 fixture
@pytest.fixture
def configured_container():
    container = ServiceContainer()
    # ... 配置 ...
    return container

def test1(configured_container):
    pass

# 不好的 - 重复代码
def test1():
    container = ServiceContainer()
    # ... 配置 ...

def test2():
    container = ServiceContainer()
    # ... 配置 ...
```

---

## 测试运行命令速查

```bash
# 基础命令
pytest                                    # 运行所有测试
pytest -v                                 # 详细输出
pytest -v tests_pytest/test_container.py   # 运行特定文件
pytest -k "container"                      # 运行匹配名称的测试

# 按标记运行
pytest -m unit                            # 单元测试
pytest -m integration                     # 集成测试
pytest -m "not slow"                       # 排除慢速测试

# 覆盖率
pytest --cov=python_backend               # 带覆盖率
pytest --cov-report=html                  # HTML 报告

# 性能测试（需要 pytest-benchmark）
pytest --benchmark-only                   # 只运行基准测试

# 失败后停止
pytest -x                                # 第一个失败后停止
pytest --maxfail=3                        # 3个失败后停止

# 显示本地变量
pytest -l                                # 失败时显示局部变量
pytest -vv                               # 更详细的输出
```

---

## 迁移 Checklist

### 从 Unittest 迁移到 Pytest

- [ ] 安装 pytest 和插件
- [ ] 创建 `pytest.ini`
- [ ] 创建 `conftest.py`
- [ ] 将 `setUp` 转换为 fixture
- [ ] 将 `self.assertX` 改为 `assert`
- [ ] 添加参数化测试
- [ ] 添加标记（@pytest.mark.unit）
- [ ] 配置覆盖率

---

## 故障排查

### Pytest 找不到测试

```bash
# 检查测试文件名
# 必须以 test_ 开头或 _test 结尾

# 检查路径
cd automation  # 切换到正确的目录
pytest tests_pytest/ -v
```

### Import 错误

```bash
# 确保 PYTHONPATH 正确
# conftest.py 应该自动设置，但可以手动设置：
export PYTHONPATH="E:\Work\Code\Lumina\python_backend;E:\Work\Code\Lumina"
```

### Fixture 未找到

```bash
# 查看可用 fixtures
pytest --fixtures

# 确保 conftest.py 在正确的位置
# 应该在 automation/ 目录下
```

---

## 总结

你现在拥有一个完整的专业测试基础设施：

1. **Pytest 配置** - 完整的 pytest.ini 和 conftest.py
2. **Fixtures 系统** - 可重用的测试组件
3. **测试示例** - 各种类型的测试示例
4. **覆盖率工具** - pytest-cov 集成
5. **文档** - 迁移指南和最佳实践

**下一步建议**:
1. 运行示例测试熟悉 pytest
2. 开始为新功能编写 pytest 测试
3. 逐步迁移现有 unittest 测试
4. 设置 CI/CD 集成
