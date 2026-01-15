# 🎉 Lumina v0.1.0 (MVP)

> AI Virtual Companion with Live2D and LLM integration

## ✨ 功能特性

- **语音对话**: 支持 SenseVoice (本地) / Whisper 语音识别
- **语音合成**: Edge TTS (在线免费) / GPT-SoVITS (本地克隆)
- **Live2D 互动**: Hiyori 角色模型,支持表情联动
- **多层记忆系统**: 短期/长期/情景记忆 (SurrealDB)
- **情感系统**: 好感度、能量值、关系演化
- **心跳服务**: 角色主动发起对话

## 💻 系统要求

| 项目     | 最低配置                   |
| :------- | :------------------------- |
| 操作系统 | Windows 10/11 (64-bit)     |
| 内存     | 4GB RAM                    |
| 存储     | 500MB 可用空间             |
| 网络     | 需要 (用于 TTS 和 LLM API) |

## 🚀 安装步骤

1. 下载 `Lumina-Setup-0.1.0.exe`
2. 双击运行安装程序
3. 安装完成后,从桌面快捷方式启动

## ⚙️ 首次配置

1. 打开设置 (齿轮图标)
2. 填入 **API Key** (支持 OpenAI / DeepSeek 兼容接口)
3. 选择麦克风设备
4. 开始对话!

## ⚠️ 已知问题

- 首次启动需要 10-20 秒加载 STT 模型
- Edge TTS 依赖网络,离线时无法发声
- 部分杀毒软件可能误报 (PyInstaller 打包特性)

## 📝 更新日志

### v0.1.0 (2026-01-09)

- 🎉 首个公开测试版本
- ✅ 完整的语音对话流程
- ✅ 情感系统 (好感度 -3 ~ +5)
- ✅ 角色记忆持久化

---

**反馈与建议**: 欢迎在 [Issues](https://github.com/CheshireMew/Lumina/issues) 提交问题
