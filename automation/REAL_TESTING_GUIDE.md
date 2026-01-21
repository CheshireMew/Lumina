# 真实测试编写指南

## 关键区别

### ❌ 玩具测试 (Teaching Examples)
```python
# 只测试自己写的代码
def test_intent_detection():
    if "hello" in input:
        return "greeting"  # 测试里的假逻辑
    assert intent == "greeting"
```
**问题**: 无法发现任何真实 bug

### ✅ 真实测试 (Production Tests)
```python
# 导入真实模块
from services.chat_service import ChatService

# 测试真实代码
def test_chat_service():
    service = ChatService()
    result = service.process("hello")  # 真实调用
    assert result.status == "success"
```
**价值**: 能发现真实 bug

---

## 我们刚刚发现的真实 Bug

运行 `tests_pytest_real/` 时发现：

### Bug 1: AsyncMock 使用错误
```
System Error: object AsyncMock can't be used in 'await' expression
```
**原因**: `get_driver()` 返回 AsyncMock，但需要先 await 才能使用

### Bug 2: Mock 参数传递验证
```
assert len(received_params) > 0  # 失败：参数没有被传递
```
**原因**: LLM 参数调用方式与预期不同

### Bug 3: Magic Mock 设置
```
AttributeError: Attempting to set unsupported magic method '__getattr__'
```
**原因**: Mock 对象不支持直接设置 `__getattr__`

---

## 真实测试的 5 个原则

### 1. 导入真实代码
```python
# ✅ 正确
from services.container import ServiceContainer

# ❌ 错误
class ServiceContainer:  # 在测试里定义
    pass
```

### 2. Mock 依赖，不 Mock 被测代码
```python
# ✅ 正确：只 mock 外部依赖
@patch('services.chat_service.services')
def test_chat(mock_services):
    service = ChatService()  # 真实代码
    # 测试真实逻辑

# ❌ 错误：mock 被测代码
@patch('services.chat_service.ChatService')
def test_chat(mock_service):
    mock_service.return_value.process.return_value = "ok"
    # 这没有测试任何东西
```

### 3. 测试真实行为，而非实现细节
```python
# ✅ 正确：测试行为
def test_container_is_singleton():
    instance1 = ServiceContainer.get_instance()
    instance2 = ServiceContainer.get_instance()
    assert instance1 is instance2  # 行为：必须是单例

# ❌ 错误：测试实现
def test_container_has_instance_attribute():
    container = ServiceContainer()
    assert hasattr(container, '_instance')  # 实现细节
```

### 4. 使用真实数据结构
```python
# ✅ 正确：使用真实数据类型
def test_with_real_message():
    message = {"role": "user", "content": "hello"}  # 真实格式
    result = service.process(message)

# ❌ 错误：使用简化的测试数据
def test_with_fake_data():
    result = service.process("hello")  # 类型不匹配
```

### 5. 测试错误路径
```python
# ✅ 测试真实错误情况
def test_uninitialized_service():
    container = ServiceContainer()
    with pytest.raises(ServiceNotInitializedError):
        container.get_gateway()  # 真实错误
```

---

## 真实测试的类型

### 1. 单元测试 (Unit Tests)
```python
def test_service_container_singleton():
    """测试单个类的行为"""
    instance1 = ServiceContainer.get_instance()
    instance2 = ServiceContainer.get_instance()
    assert instance1 is instance2
```

### 2. 集成测试 (Integration Tests)
```python
@pytest.mark.asyncio
async def test_chat_service_integration():
    """测试多个组件协同工作"""
    service = ChatService()
    async for chunk in service.chat_stream("hello"):
        assert len(chunk) > 0
```

### 3. 错误处理测试 (Error Handling)
```python
def test_service_not_initialized():
    """测试错误情况"""
    with pytest.raises(ServiceNotInitializedError):
        ServiceContainer().get_gateway()
```

### 4. 并发测试 (Concurrency)
```python
def test_thread_safety():
    """测试并发访问"""
    import threading
    threads = [threading.Thread(target=get_instance) for _ in range(10)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    # 验证没有竞态条件
```

### 5. 性能测试 (Performance)
```python
def test_performance():
    """测试性能指标"""
    start = time.time()
    for _ in range(1000):
        ServiceContainer.get_instance()
    elapsed = time.time() - start
    assert elapsed < 0.1  # 必须足够快
```

---

## 测试文件组织

### 推荐结构
```
automation/
├── tests/                    # 真实 unittest 测试 (40 文件)
│   ├── services/
│   ├── backend/
│   └── core/
│
├── tests_pytest_real/        # 真实 pytest 测试 (新增)
│   ├── test_real_container.py      # ✅ 测试真实代码
│   └── test_real_chat_service.py    # ✅ 测试真实代码
│
├── tests_pytest/             # 教学示例 (15 文件)
│   ├── test_container_pytest.py    # ⚠️ 部分 + 部分假
│   ├── test_chat_parametrized.py   # ❌ 只演示功能
│   └── ...
│
└── examples/                 # 将来的示例文件夹
    └── pytest_tutorial.py    # 教学示例移到这里
```

---

## 如何编写真实测试

### 步骤 1: 找到要测试的真实代码
```bash
# 查看项目结构
python_backend/services/chat_service.py
python_backend/services/container.py
python_backend/core/events/bus.py
```

### 步骤 2: 编写测试导入
```python
import sys
from pathlib import Path
PROJECT_ROOT = Path(__file__).parents[2]
sys.path.insert(0, str(PROJECT_ROOT / "python_backend"))

from services.chat_service import ChatService  # 真实导入
```

### 步骤 3: Mock 外部依赖
```python
from unittest.mock import patch, AsyncMock

@patch('services.chat_service.services')
def test_chat_service(mock_services):
    # 只 mock 外部依赖
    mock_services.soul = MagicMock()
    # 测试真实逻辑
```

### 步骤 4: 测试真实行为
```python
def test_behavior():
    service = ChatService()  # 真实代码
    result = service.do_something()  # 真实调用
    assert result == expected_value  # 真实验证
```

### 步骤 5: 运行测试
```bash
pytest tests_pytest_real/test_real_container.py -v
```

---

## 检查清单

当你写测试时，问自己：

- [ ] 是否导入了真实的 `python_backend` 模块？
- [ ] 是否创建了真实的类实例（不是 mock）？
- [ ] 是否调用了真实的方法（不是 mock）？
- [ ] 是否验证了真实的行为（不是 mock 的返回值）？
- [ ] 如果这个测试失败了，是否意味着真实代码有 bug？

**如果全部是 "是"，这就是真实测试！**

---

## 下一步

1. **删除或移动玩具测试**
   ```bash
   mv tests_pytest/test_chat_parametrized.py examples/
   mv tests_pytest/test_data_driven.py examples/
   ```

2. **扩展真实测试**
   ```bash
   # 为每个关键服务编写真实测试
   tests_pytest_real/test_real_llm_manager.py
   tests_pytest_real/test_real_memory_service.py
   tests_pytest_real/test_real_plugin_system.py
   ```

3. **更新 CI/CD**
   ```yaml
   # 只运行真实测试
   pytest automation/tests/              # unittest
   pytest tests_pytest_real/             # 真实 pytest
   pytest tests_pytest/e2e/              # E2E 测试
   ```

---

## 总结

| 特征 | 玩具测试 | 真实测试 |
|------|---------|---------|
| 导入真实代码 | ❌ | ✅ |
| 测试真实逻辑 | ❌ | ✅ |
| 能发现 bug | ❌ | ✅ |
| 有生产价值 | ❌ | ✅ |
| 适合教学 | ✅ | ✅ |

**结论**:
- 玩具测试适合学习 pytest 功能
- 真实测试适合保证代码质量
- 生产环境应该只运行真实测试
