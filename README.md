# Lumina

Lumina 是一个本地优先的 Windows 桌面 AI 伴侣。当前产品把文本与语音对话、长期记忆、视觉理解和 Live2D 形象收束成一个稳定、亲切、长期可用的单角色体验。

它不是 Agent 工作台，不是插件平台，也不是 GalGame 养成游戏。

## 当前边界

保留：

- 单角色，默认 Hiyori。
- Live2D 形象、表情、动作和口型联动。
- 文本对话和语音对话。
- VAD、STT、声纹识别、TTS。
- 图片与屏幕视觉理解。
- 长期记忆和会话上下文。
- 轻量主动性，用于陪伴和提醒。
- 内部 provider/capability 机制，用于装配系统能力。

不再恢复：

- 多角色、角色市场和角色切换器。
- VRM、Sprite 或其它非 Live2D 形象运行时。
- 剧情章节、好感度、能量值、关系等级等游戏化数值。
- 直播、弹幕和插件市场。
- 面向用户的 Agent 编排、插件上传与动态插件界面。

## 架构

```text
Electron + React
  - 桌面窗口、聊天与设置
  - Live2D 渲染
  - 音频采集和播放

Python FastAPI 主进程
  - 对话、角色、记忆与模型调用
  - 运行状态与 Worker 管理

Worker 进程
  - STT、TTS、Vision

本地 SQLite
  - 对话历史与长期记忆
  - Worker 状态、审计记录和声纹元数据
  - 开箱即用，不依赖 Docker 或外部数据库
```

主进程只接受带有本次启动身份的 Lumina 后端和 Worker。退出桌面端时会先请求各进程正常关闭，超时后再清理对应的 Windows 进程树，避免误用旧进程或留下孤儿进程。

## 目录

```text
app/                 Electron + React 前端
core/                Electron 侧服务和后端桥接
python_backend/      FastAPI 后端、Worker、记忆和聊天编排
public/              Live2D/Cubism 等前端静态资源
assets/              图标、音频等桌面资源
config/              模型、端口和运行时配置
scripts/             构建、类型生成和验证脚本
automation/          维护中的测试代码
```

## Windows 运行

准备 Node.js 20+ 与 Python 3.10+，然后安装依赖：

```powershell
npm install
python -m pip install -r python_backend/requirements.txt
```

正常启动：

```powershell
.\start_lumina.ps1
```

强制使用开发模式：

```powershell
.\start_lumina.ps1 -Dev
```

启动脚本会直接运行 Electron、Vite 和 Python 后端，不会启动 Docker，也不要求 PostgreSQL。若确实需要调试旧的 PostgreSQL 记忆驱动，可额外安装 `python_backend/requirements-postgres.txt`，并显式设置 `LUMINA_MEMORY_PROVIDER=driver.memory.postgres`；这不是桌面应用的默认运行方式。

## 本地数据与日志

开发环境的可变数据统一写入仓库根目录下被 Git 忽略的 `Lumina_Data/`。安装版写入 Electron 提供的用户数据目录，不会写入安装目录，卸载时也不会自动删除用户数据。主要内容包括：

- `database/lumina.sqlite3`：对话历史、长期记忆、运行状态与本地审计数据。
- `sessions/` 与 `characters/`：会话状态和用户修改后的角色配置。
- `backgrounds/` 与声纹目录：用户导入的本地素材。
- `logs/`：自动轮转的运行日志。

普通日志只记录模型名、消息数量、字符数、耗时和错误摘要，不记录完整提示词、对话、长期记忆或模型思考内容。只有显式设置 `LUMINA_DIAGNOSTIC_MODEL_CONTENT=1` 时，才会在 `logs/model-diagnostics.log` 中写入模型诊断内容；排查结束后应关闭该选项并妥善处理诊断日志。

## 验证

日常提交前运行：

```powershell
npm run verify-build
npm run lint
npx tsc --noEmit
npm test
npm run test:python
```

`verify-build` 会检查配置、默认 SQLite 依赖、卸载数据保留策略，以及 STT、TTS、Vision 等运行时入口是否真实存在。GitHub Actions 使用同一组 Windows 检查。性能耗时与安全回归工作流只按需手动触发。

发布维护者可使用下面的命令生成 Windows 安装包：

```powershell
npm run build
```

该命令会构建主后端与各 Worker 运行时、校验产物身份和哈希、编译前端并调用 Electron Builder。源码检查不需要执行打包命令。

## 开发原则

- 新功能必须服务“有温度的 AI 伴侣”这个主线。
- 不为了扩展性恢复插件生态。
- 不为了趣味性恢复游戏化数值。
- 不恢复多角色和多形象运行时。
- 长期产品边界保留在这个 README；重构执行边界见 `docs/companion-runtime-refactor.md`。
- `AGENTS.md` 是给编码 Agent 的工作规则，不属于产品文档。

## 许可证

Lumina 自有源码使用 `GPL-3.0-or-later`。完整条款见 `LICENSE` 与 `LICENSING.md`。Live2D Cubism、Hiyori 示例模型、预编译运行库和其它依赖仍受各自条款约束，详情见 `THIRD_PARTY_NOTICES.md`。
