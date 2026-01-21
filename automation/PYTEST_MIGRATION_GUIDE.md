# Pytest 迁移指南

## 为什么要迁移到 Pytest？

### Unittest vs Pytest 对比

| 特性 | Unittest | Pytest |
|------|----------|--------|
| **代码量** | 更多样板代码 | 更简洁 |
| **断言** | `self.assertEqual()` | `assert a == b` |
| **参数化测试** | 需要手动循环 | 内置 `@parametrize` |
| **Fixtures** | `setUp/tearDown` | 更强大的 `@fixture` |
| **插件生态** | 有限 | 丰富的插件 |
| **错误信息** | 基础 | 详细的上下文 |
| **测试发现** | 需要继承 TestCase | 自动发现 |

---

## 快速开始

### 1. 安装依赖

```bash
pip install pytest pytest-asyncio pytest-cov pytest-xdist
pip install hypothesis  # 可选：属性测试
pip install aiohttp    # 可选：异步HTTP测试
```

### 2. 运行测试

```bash
# 运行所有 pytest 测试
cd automation
pytest tests_pytest/ -v

# 运行带覆盖率的测试
python run_pytest_with_coverage.py

# 只运行单元测试
pytest -m unit -v

# 运行特定文件
pytest tests_pytest/test_container_pytest.py -v

# 运行匹配名称的测试
pytest -k "container" -v
```

---

## Unittest 到 Pytest 转换示例

### 示例 1: 基础测试

**Unittest:**
```python
import unittest
from services.container import ServiceContainer

class TestServiceContainer(unittest.TestCase):
    def setUp(self):
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    def test_singleton_pattern(self):
        instance1 = ServiceContainer.get_instance()
        instance2 = ServiceContainer.get_instance()
        self.assertIs(instance1, instance2)
        print("✅ Singleton pattern verified")
```

**Pytest:**
```python
import pytest
from services.container import ServiceContainer

def test_singleton_pattern():
    ServiceContainer._instance = None
    instance1 = ServiceContainer.get_instance()
    instance2 = ServiceContainer.get_instance()
    assert instance1 is instance2
    # 无需 print - pytest 自动显示通过/失败
```

### 示例 2: 参数化测试

**Unittest:**
```python
class TestValidation(unittest.TestCase):
    def test_valid_inputs(self):
        valid_inputs = ["test.plugin", "my_extension", "vendor.name"]
        for inp in valid_inputs:
            self.assertTrue(validate_plugin_id(inp))

    def test_invalid_inputs(self):
        invalid_inputs = ["../etc/passwd", "plugin with spaces"]
        for inp in invalid_inputs:
            self.assertFalse(validate_plugin_id(inp))
```

**Pytest:**
```python
@pytest.mark.parametrize("plugin_id,expected_valid", [
    ("test.plugin", True),
    ("my_extension", True),
    ("../etc/passwd", False),
    ("plugin with spaces", False),
])
def test_plugin_id_validation(plugin_id, expected_valid):
    assert validate_plugin_id(plugin_id) == expected_valid
```

### 示例 3: Fixtures

**Unittest:**
```python
class TestChat(unittest.TestCase):
    def setUp(self):
        self.mock_llm = MagicMock()
        self.mock_soul = MagicMock()
        self.mock_container = ServiceContainer()

    def test_chat_with_mock(self):
        # Use self.mock_llm, etc.
        pass
```

**Pytest:**
```python
# Fixtures 定义在 conftest.py 中，自动可用
def test_chat_with_mock(mock_llm_manager, mock_soul_service, mock_container):
    # Fixtures 自动注入
    pass
```

---

## Pytest 高级特性

### 1. 参数化测试

```python
# 单个参数
@pytest.mark.parametrize("input", [1, 2, 3])
def test_single_param(input):
    assert input > 0

# 多个参数
@pytest.mark.parametrize("x,y,expected", [
    (1, 2, 3),
    (5, 5, 10),
])
def test_add(x, y, expected):
    assert x + y == expected

# 使用自定义 IDs
@pytest.mark.parametrize("value", [1, 2, 3], ids=["one", "two", "three"])
def test_with_ids(value):
    assert value > 0
```

### 2. Marks（标记）

```python
# 定义标记
@pytest.mark.unit
def test_something():
    pass

@pytest.mark.slow
def test_slow_operation():
    pass

@pytest.mark.parametrize("x", [1, 2, 3])
@pytest.mark.unit
def test_parametrized_with_mark(x):
    pass

# 运行特定标记的测试
# pytest -m unit
# pytest -m "not slow"
```

### 3. Skip 和 Xfail

```python
# 跳过测试
@pytest.mark.skip(reason="Not implemented yet")
def test_not_ready():
    pass

# 条件跳过
@pytest.mark.skipif(sys.version_info < (3, 8), reason="Need 3.8+")
def test_python38_only():
    pass

# 预期失败
@pytest.mark.xfail(reason="Known bug")
def test_known_failure():
    assert False

# 运行时预期失败
@pytest.mark.xfail(raises=ValueError)
def test_expected_to_fail():
    raise ValueError()
```

### 4. 异步测试

```python
import pytest

@pytest.mark.asyncio
async def test_async_operation():
    result = await async_function()
    assert result is not None
```

### 5. Fixtures

```python
# 简单 fixture
@pytest.fixture
def data():
    return {"key": "value"}

def test_with_fixture(data):
    assert data["key"] == "value"

# 带清理的 fixture
@pytest.fixture
def temp_file():
    file = tempfile.NamedTemporaryFile(delete=False)
    yield file.name
    os.unlink(file.name)

# 不同作用域
@pytest.fixture(scope="session")  # 全局一次
def session_data():
    return {}

@pytest.fixture(scope="module")   # 每个模块一次
def module_data():
    return {}

@pytest.fixture(scope="function")  # 每个测试一次（默认）
def function_data():
    return {}
```

---

## 测试覆盖率

### 生成覆盖率报告

```bash
# 命令行输出
pytest --cov=python_backend --cov-report=term-missing

# HTML 报告
pytest --cov=python_backend --cov-report=html

# XML 报告（用于 CI）
pytest --cov=python_backend --cov-report=xml

# 组合
pytest --cov=python_backend --cov-report=term-missing --cov-report=html --cov-report=xml
```

### 使用提供的脚本

```bash
# 运行所有测试 + 覆盖率
python run_pytest_with_coverage.py

# 只运行单元测试
python run_pytest_with_coverage.py --unit

# 生成 HTML 报告
python run_pytest_with_coverage.py --html
```

---

## 属性测试（Property-Based Testing）

使用 Hypothesis 自动生成数百个测试用例：

```bash
pip install hypothesis
```

```python
from hypothesis import given, strategies as st

@given(st.text(min_size=1, max_size=100))
def test_text_never_crashes(text):
    # 自动生成 100 个随机字符串测试
    result = process_text(text)
    assert result is not None
```

---

## 测试文件组织

### 推荐结构

```
automation/
├── conftest.py                    # 共享 fixtures
├── pytest.ini                     # Pytest 配置
├── fixtures/                      # 可重用的 fixtures
│   ├── __init__.py
│   ├── factories.py               # 测试数据工厂
│   ├── data_generators.py         # 随机数据生成
│   └── mock_servers.py            # Mock HTTP 服务器
├── tests/                         # 现有 unittest 测试
├── tests_pytest/                  # 新的 pytest 测试
│   ├── test_container_pytest.py
│   ├── test_chat_parametrized.py
│   ├── test_property_based.py
│   └── test_with_fixtures.py
└── run_pytest_with_coverage.py    # 测试运行脚本
```

---

## 迁移策略

### 阶段 1: 并行运行（推荐）

保持现有 unittest 测试，添加新的 pytest 测试：

```
automation/
├── tests/           # 保留现有 unittest 测试
└── tests_pytest/    # 新测试使用 pytest
```

### 阶段 2: 逐个迁移

将 unittest 测试逐个转换为 pytest：

1. 移除 `unittest.TestCase` 继承
2. 移除 `self` 参数
3. 将 `setUp` 改为 fixture
4. 将断言改为 `assert`
5. 添加参数化

### 阶段 3: 完全迁移

完成所有测试迁移后，可以：
- 删除 `tests/` 目录
- 重命名 `tests_pytest/` 为 `tests/`

---

## 常见问题

### Q: 如何混合运行 unittest 和 pytest 测试？

A: Pytest 可以自动发现并运行 unittest 测试：

```bash
# 运行所有测试（包括 unittest）
pytest -v

# 只运行 pytest 测试
pytest tests_pytest/ -v

# 只运行 unittest 测试
pytest tests/ -v
```

### Q: 如何在 pytest 中使用现有的 setUp 逻辑？

A: 将其转换为 fixture：

```python
# Unittest
def setUp(self):
    self.container = ServiceContainer()
    self.mock_llm = MagicMock()

# Pytest
@pytest.fixture
def container_with_mock():
    container = ServiceContainer()
    mock_llm = MagicMock()
    container._llm_manager = mock_llm
    return container

def test_something(container_with_mock):
    # 使用 fixture
    pass
```

### Q: 如何处理异步测试？

A: 使用 `pytest-asyncio`：

```python
import pytest

@pytest.mark.asyncio
async def test_async():
    result = await async_function()
    assert result is not None
```

---

## 最佳实践

1. **使用描述性的测试名称**
   ```python
   # 好的命名
   def test_user_login_with_invalid_credentials_raises_error():
       pass

   # 不好的命名
   def test_login():
       pass
   ```

2. **一个测试只验证一件事**
   ```python
   # 好
   def test_login_returns_token_on_success():
       pass

   def test_login_raises_error_on_invalid_credentials():
       pass

   # 不好
   def test_login():
       # 测试了太多事情
       pass
   ```

3. **使用 fixtures 复用代码**
   ```python
   # 好 - 使用 fixture
   def test_with_fixture(mock_container):
       pass

   # 不好 - 重复代码
   def test1():
       container = ServiceContainer()
       # ...

   def test2():
       container = ServiceContainer()
       # ...
   ```

4. **使用 marks 分类测试**
   ```python
   @pytest.mark.unit
   def test_fast_unit_test():
       pass

   @pytest.mark.integration
   def test_slow_integration_test():
       pass
   ```

---

## 资源

- [Pytest 文档](https://docs.pytest.org/)
- [Hypothesis 文档](https://hypothesis.readthedocs.io/)
- [Pytest-Cov 文档](https://pytest-cov.readthedocs.io/)
