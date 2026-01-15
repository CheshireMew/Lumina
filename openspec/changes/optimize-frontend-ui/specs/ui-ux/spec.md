# Spec: UI/UX Improvements

## 新增需求

### 需求:沉浸式聊天体验 (Immersive Chat)

#### 场景:消息气泡动态样式

- **Given** 用户或 AI 发送消息。
- **When** 消息显示在聊天窗口中。
- **Then** 气泡应当具备:
  - 微弱的阴影和圆角(Modern UI)。
  - 区分明显的颜色(用户 vs AI)。
  - 进场动画(Fade-in + Slide-up)。

### 需求:麦克风状态反馈 (Microphone Feedback)

#### 场景:语音输入状态

- **Given** 用户点击麦克风图标。
- **When** 系统进入"监听"状态。
- **Then** 麦克风图标必须 (MUST) 显示明显的波纹或闪烁动画。
- **And** 只有在 VAD 检测到语音时,波形才剧烈波动。

### 需求:HUD 状态展示 (HUD Visualization)

#### 场景:情感能量变化

- **Given** 收到后端 `state_update` 事件。
- **When** `energy` 或 `mood` 值发生变化。
- **Then** HUD 条(Bar)必须 (MUST) 平滑过渡到新值(CSS transition)。
- **And** 颜色应根据数值范围动态变化(如低能量变红)。
