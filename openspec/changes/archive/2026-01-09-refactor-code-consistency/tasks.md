## 1. 实施

- [x] 1.1 修改 `schemas/requests.py`:
  - [x] 将 `char_name` 重命名为 `character_name` (Field alias="char_name")
  - [x] 移除 `character_id` 默认值 (设为 Optional)
- [x] 1.2 修改 `routers/memory.py` & `routers/soul.py`:
  - [x] 更新 `char_name` -> `character_name`
  - [x] 处理 `character_id` 回退逻辑 (check global config)
- [x] 1.3 扫描 `surreal_memory.py`:
  - [x] 文档 `fact` -> `memory`
  - [x] 移除 `content as text` 别名 (Use native DB field name)
- [x] 1.4 修改 `routers/memory.py`:
  - [x] 适配 `content` 字段名变更 (r.get("content"))
  - [x] 清理局部变量 `char_name`
