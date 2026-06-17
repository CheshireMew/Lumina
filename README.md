# Lumina

Lumina 是一个本地优先的桌面 AI 伴侣。当前目标是把语音、记忆、视觉和 Live2D 形象收束成一个稳定、亲切、长期可用的单角色体验。

它不是 Agent 工作台，不是插件平台，也不是 GalGame 养成游戏。

## 当前边界

保留：

- 单角色，默认 Hiyori。
- Live2D 形象、表情、动作和口型联动。
- 文本对话和语音对话。
- VAD、STT、声纹识别、TTS。
- Vision 图像/屏幕理解。
- 长期记忆和会话上下文。
- 轻量主动性，用于陪伴和提醒。
- 内部 provider/capability 机制，用于 STT、TTS、Vision、声纹等系统能力装配。

删除或不再恢复：

- 多角色、角色市场、角色切换器。
- VRM、Sprite 或其它非 Live2D 形象运行时。
- GalGame HUD、剧情章节、好感度、能量值、关系等级、Lv、进度条、雷达图、PAD 数值面板。
- Bilibili、弹幕、直播互动。
- 插件商店、插件上传、marketplace、插件 UI slot、动态插件路由。
- 大量研究报告、旧审计、旧迁移、剧情草案和插件开发文档。

## 架构

```text
Electron + React
  - 桌面窗口
  - 聊天 UI
  - 设置
  - Live2D 渲染
  - 音频采集和播放

Python FastAPI 主进程
  - Chat pipeline
  - Soul / Character
  - Memory
  - LLM routes
  - Runtime state
  - Worker control

Worker 进程
  - STT
  - TTS
  - Vision

PostgreSQL + pgvector
  - 对话日志
  - 向量记忆
  - 运行状态
```

## 目录

```text
app/                 Electron + React 前端
core/                Electron 侧服务和后端桥接
python_backend/      FastAPI 后端、Worker、记忆和聊天编排
public/              Live2D/Cubism 等前端静态资源
assets/              图标、音频等桌面资源
config/              LLM registry、端口和配置模板
scripts/             构建、类型生成和验证脚本
automation/          测试代码
```

## 运行

```powershell
npm install
.\start_lumina.ps1
```

开发模式：

```powershell
npm run dev
```

后端依赖：

```powershell
cd python_backend
python -m venv venv
.\venv\Scripts\activate
pip install -r requirements.txt
```

常用检查：

```powershell
npm run lint
npx tsc --noEmit
python -m compileall -q python_backend
```

完整构建：

```powershell
npm run build
```

注意：当前 `npm run build` 会先执行后端打包脚本。如果本机 Python 是 3.10，可能因 `datetime.UTC` 不存在而失败。使用 Python 3.11+，或把打包脚本改为 `datetime.timezone.utc`。

## 开发原则

- 新功能必须服务“有温度的 AI 伴侣”这个主线。
- 不为了扩展性恢复插件生态。
- 不为了趣味性恢复游戏化数值。
- 不恢复多角色和多形象运行时。
- 长期产品边界保留在这个 README；重构执行边界见 `docs/companion-runtime-refactor.md`。
- `AGENTS.md` 是给编码 Agent 的工作规则，不属于产品文档。
