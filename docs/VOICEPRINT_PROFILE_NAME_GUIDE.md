# Profile Name 填写说明

## 什么是 Profile Name？

`profile_name` 是**声纹配置文件的名称**，用于标识不同的声纹样本。

## 填写建议

### 默认值
- **`default`**（推荐新手使用）
- 直接按回车即可

### 自定义名称
根据使用场景命名：
- `my_voice` - 我的声音
- `work` - 工作状态
- `casual` - 放松状态  
- `tired` - 疲劳时声音
- `morning` - 早晨声音

## 存储位置

填写 `{name}` 后，声纹会保存为：
```
voiceprint_profiles/{name}.npy
```

例如：
- `default` → `voiceprint_profiles/default.npy`
- `my_voice` → `voiceprint_profiles/my_voice.npy`

## 多 Profile 使用

可以创建多个声纹 Profile，在不同场景切换：

```bash
# 录制工作状态声纹
python register_voiceprint.py
# 输入: work

# 录制放松状态声纹  
python register_voiceprint.py
# 输入: casual
```

在设置界面的 "Profile 名称" 输入框中切换即可。

---

**建议**：首次使用直接用 `default`，熟悉后再创建多个 Profile。
