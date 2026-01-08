## 1. 实施修复

- [x] 1.1 在 `surreal_memory.py` 中实现 `parse_res` 辅助函数（解决 KeyError）。
- [x] 1.2 在 `surreal_memory.py` 中实现 `safe_id` 辅助函数（解决 SQL 转义问题）。
- [x] 1.3 更新 `test_merge.py` 以验证这两个辅助函数的逻辑。
- [x] 1.4 添加 `import os` 修复 `_load_aliases` 静默失败的 bug。

## 2. 验证

- [x] 2.1 用户重启后端。
- [x] 2.2 用户点击前端 "Merge & Clean" 按钮。
- [x] 2.3 验证日志中出现成功合并信息（Merged Aliases: 2）。
- [x] 2.4 验证别名实体已被删除（柴郡 -> Cheshire, Hiyori -> hiyori）。
