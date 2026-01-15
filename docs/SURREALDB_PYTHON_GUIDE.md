# SurrealDB Python Driver Guide (Lumina Project)

本文档记录了本项目中使用的 `SurrealDriver` (`python_backend/plugins/drivers/memory/surreal_driver.py`) 的行为规范，特别是其返回值格式。为了避免 Python 客户端与 HTTP REST API 的返回值混淆，请仔细阅读。

## 核心区别 (Critical)

| 操作方式                           | 返回值结构       | 示例                                         |
| :--------------------------------- | :--------------- | :------------------------------------------- |
| **HTTP REST API** (`curl`)         | 包装对象列表     | `[{"status": "OK", "result": [...data...]}]` |
| **Python Client** (`driver.query`) | **直接数据列表** | `[{"id": "...", "name": "..."}]`             |

> ⚠️ **常见错误**：在 Python 代码中不要尝试读取 `.get('result')`，直接使用返回的 List 即为数据结果。

---

## 依赖注入与初始化

通常通过 `ServiceContainer` 获取已初始化的单例，而不是直接实例化 Driver。

```python
from services.container import services

async def my_function():
    # 获取核心 Memory 系统 (封装了 Driver)
    surreal = services.get_surreal()

    # 1. 执行原生 SQL (推荐用于复杂查询)
    results = await surreal.execute_raw_query("SELECT * FROM conversation_log LIMIT 5;")

    # 2. 调用封装方法
    # await surreal.log_conversation(...)
```

---

## CRUD 操作速查

### 1. 查询 (SELECT / Query)

- **方法**: `execute_raw_query(sql, params)` 或 `driver.query(sql, params)`
- **返回值**: `List[Dict]` (记录列表) 或 `Dict` (如果只返回单条统计消息，取决于具体情况，但通常是列表)

```python
# ✅ 正确写法
results = await surreal.execute_raw_query("SELECT * FROM table WHERE id = $id", {"id": "123"})
if results:
    print(results[0]["character_id"])

# ❌ 错误写法 (HTTP API 思维)
# data = results[0]["result"] # 报错！KeyError
```

**统计查询示例**:

```python
res = await surreal.execute_raw_query("SELECT count() FROM table GROUP ALL")
# 返回: [{'count': 123}]
count = res[0]['count'] if res else 0
```

### 2. 创建 (CREATE)

- **方法**: `driver.create(table, data)`
- **返回值**: `str` (新记录的 ID，e.g., `"table_name:random_id"`)

```python
new_id = await surreal.driver.create("conversation_log", {
    "narrative": "Something happened",
    "created_at": datetime.now().isoformat()
})
# new_id = "conversation_log:kx82..."
```

### 3. 更新 (UPDATE / MERGE)

- **方法**: `driver.update(table, id, data)`
- **行为**: 执行 `MERGE` (局部更新)。如果需要完全替换，请使用 SQL。
- **返回值**: `bool` (True 表示成功，False 表示捕获了异常)

```python
success = await surreal.driver.update("user_profile", "user_123", {
    "last_seen": datetime.now().isoformat()
})
```

### 4. 删除 (DELETE)

- **方法**: `driver.delete(table, id)`
- **返回值**: `bool` (True 表示成功)

```python
await surreal.driver.delete("conversation_log", "log_id_123")
```

---

## 常用 SurrealQL 语法片断

### 数组操作

```sql
-- 向数组添加 tag
UPDATE target:123 SET tags += 'funny';

-- 移除 tag
UPDATE target:123 SET tags -= 'boring';
```

### 图关系 (Graph)

```sql
-- 创建关系 (自动去重)
RELATE user:a->likes->post:b SET created_at = time::now();

-- 查询关系
SELECT ->likes->post.* FROM user:a;
```

### 全文检索 (如果不使用 Vector)

本项目已配置 `my_analyzer`。

```sql
SELECT * FROM episodic_memory
WHERE content @@ 'some keyword';
```

---

## 调试工具

如果你不确定返回什么，请使用项目根目录下的临时脚本 `debug_db.py` 进行测试 (仿照本次修复时的做法)。

```python
# debug_db.py 模板
import asyncio
from python_backend.plugins.drivers.memory.surreal_driver import SurrealDriver

async def test():
    driver = SurrealDriver()
    await driver.connect()
    res = await driver.query("SELECT * FROM conversation_log LIMIT 1;")
    print(f"Type: {type(res)}")
    print(f"Data: {res}")
    await driver.close()

if __name__ == "__main__":
    asyncio.run(test())
```

---

## 技术陷阱与最佳实践 (Pitfalls & Best Practices)

### 1. 向量序列化 (Vector Serialization)

**问题**: `sentence-transformers` 等模型通常返回 `numpy.ndarray` 格式的向量。
**风险**: 如果直接传给 `SurrealDB` 客户端，会报错 `no encoder for type strict` 或悄无声息地失败（取决于版本）。
**解决**: 必须显式转换为 Python List。

```python
query_vec = encoder("text")
if hasattr(query_vec, 'tolist'):
    query_vec = query_vec.tolist() # CRITICAL
await driver.search_vector(..., vector=query_vec)
```

### 2. 混合检索阈值 (Hybrid Search Threshold)

**问题**: 默认阈值 (如 0.6) 在多语言或短文本匹配中可能过于严格。
**建议**:

- **Baseline**: 建议从 `0.45` 开始。
- **降级策略 (Gradient Degradation)**: 如果搜索结果不足（例如 < 3 条），应实施自动重试机制，每次降低阈值 (e.g., -0.1)，直到达到最低安全线 (e.g., 0.25)。不要假设一次查询就能返回完美结果。

### 3. ID 格式

**注意**: SurrealDB 的 ID 是 `table:id` 格式的 RecordID。但是在 Python 客户端返回的结果中，ID 字段会被自动解析。

- 写入时: 如果手动指定 ID，字符串格式如 `"conversation_log:kx82..."` 会被正确识别。
- 读取时: 确保处理 ID 时能兼容字符串或 RecordID 对象。我们的 Driver 封装了 `_extract_id` 帮助方法来统一处理。
