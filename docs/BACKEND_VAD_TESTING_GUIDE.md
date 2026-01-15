# 后端 VAD 迁移 - 安装与测试指南

## 📦 安装步骤

### 1. 安装 Python 后端依赖

```powershell
cd python_backend
pip install sounddevice
```

**验证安装**:
```powershell
python -c "import sounddevice as sd; print(sd.query_devices())"
```

如果成功,你会看到系统的音频设备列表。

---

##  实施 测试步骤

### 2. 启动后端服务

```powershell
cd python_backend
python stt_server.py
```

**预期输出**:
```
INFO:     Uvicorn running on http://127.0.0.1:8765
[AudioManager] initialized and started
```

### 3. 测试音频设备 API

打开浏览器或使用 `curl` 测试:

```powershell
# 获取音频设备列表
curl http://127.0.0.1:8765/audio/devices
```

**预期响应**:
```json
{
  "devices": [
    {"index": 0, "name": "Microphone (Realtek)", "channels": 2},
    {"index": 1, "name": "立体声混音", "channels": 2}
  ],
  "current": "Microphone (Realtek)"
}
```

```powershell
# 设置音频设备
curl -X POST http://127.0.0.1:8765/audio/config `
  -H "Content-Type: application/json" `
  -d '{"device_name": "Microphone (Realtek)"}'
```

**预期响应**:
```json
{
  "status": "success",
  "device_name": "Microphone (Realtek)"
}
```

### 4. 启动 Electron 前端

在另一个终端:

```powershell
cd e:\Work\Code\Lumina
npm run dev
```

### 5. 测试完整流程

1. **打开设置**:点击齿轮图标 ⚙️
2. **切换到 Voice 标签页**
3. **查看音频设备选择器**:
   - 应该能看到"Audio Input Device"部分
   - 下拉菜单中应显示你的麦克风列表
   - 选择你的物理麦克风(**避免选"立体声混音"**)

4. **测试语音输入**:
   - 对着麦克风说话
   - **预期行为**:
     - 说话时:圆形图标变为 🎤,边框发光,显示"Listening..."
     - 说话结束:图标变为 ⏳,显示"Thinking..."
     - 转录完成:显示文字内容,然后自动发送

---

## 🐛 常见问题排查

### 问题1:`sounddevice` 安装失败

**Windows 解决方案**:
```powershell
# 方法1:使用预编译包
pip install sounddevice --no-cache-dir

# 方法2:如果还是失败,安装 PortAudio
# 下载 PortAudio DLL:https://github.com/spatialaudio/portaudio-binaries/releases
# 将 DLL 放到 Python Scripts 目录
```

### 问题2:AudioManager 启动失败

**检查日志**:
```
[AudioManager] 启动音频捕获失败: ...
```

**可能原因**:
- 麦克风被其他程序占用(关闭 Discord、Teams等)
- 设备权限不足(以管理员身份运行)

### 问题3:前端无法获取设备列表

**检查**:
1. 后端服务是否在 `http://127.0.0.1:8765` 运行
2. 浏览器控制台是否有 CORS 错误(应该不会有,已配置)
3. `stt_server.py` 日志是否有错误

### 问题4:仍然捕获到系统音频

**确认步骤**:
1. 在设置中选择的是物理麦克风,而非"立体声混音"或"虚拟音频设备"
2. Windows 声音设置中,确保麦克风不是"侦听此设备"状态
   - 右键任务栏音量图标 → 声音 → 录制 → 麦克风属性 → 侦听 → 取消勾选

---

## ✅ 验证清单

- [ ] `pip install sounddevice` 成功
- [ ] 后端启动无错误
- [ ] `/audio/devices` API 返回设备列表
- [ ] 前端设置页显示设备选择器
- [ ] 选择物理麦克风后,后端日志显示切换成功
- [ ] 对着麦克风说话,UI 有反馈(Listening → Thinking)
- [ ] 转录结果正确显示
- [ ] **关键测试**:播放音乐时说话,确认不会把音乐内容误识别

---

## 🎯 成功标准

**后端 VAD 迁移成功的标志**:
1. ✅ 能够选择特定的麦克风设备
2. ✅ 只捕获麦克风音频,不捕获电脑播放的音频
3. ✅ 语音活动检测(VAD)准确触发
4. ✅ 转录结果正确传递到前端
5. ✅ UI 状态(Listening/Thinking/Idle)正确显示

---

## 🔄 回退方案(如果出现问题)

如果新方案有问题,可以临时回退到旧的前端 VAD:

1. 重新安装前端 VAD 依赖:
   ```powershell
   npm install @ricky0123/vad-react
   ```

2. Git 回退 `VoiceInput.tsx` 到旧版本:
   ```powershell
   git checkout HEAD~1 app/renderer/components/VoiceInput.tsx
   ```

3. 注释掉 `stt_server.py` 中的 `audio_manager.start()`

**但请优先排查问题,新方案才能彻底解决回环问题!**
