# Proposal: Package Lite Distribution (MVP)

## Summary

构建 **Lumina Lite (MVP)** 发行版,旨在提供一个轻量级、开箱即用的 Windows 安装包。
核心策略是 **"Hybrid Local"**:保留本地核心逻辑(Electron + Python Backend + DB),但默认利用云端/轻量级模型以减小体积和性能门槛。

## 为什么

1. **用户门槛**:完整版依赖本地大模型(3GB+)和高配 GPU,阻碍了普通用户体验。
2. **反馈迭代**:需要一个快速分发的版本给早期用户测试 UI 和交互流程。
3. **部署复杂**:目前依赖手动安装 Python/Node 环境,极其繁琐。

## 变更内容

### 1. 默认配置 (Lightweight Profile)

- **STT**: 默认使用 **SenseVoice** (Sherpa-ONNX)。
  - _理由_: 相比 Whisper Tiny 准确率更高,体积极小 (~50MB),且支持情感识别。
- **TTS**: 默认使用 **Edge TTS**。
  - _理由_: 无需本地模型,零磁盘占用,效果自然(依赖网络)。
- **LLM**: 默认配置为 **Compatible API (Cloud)**。
  - _理由_: 避免捆绑 Ollama/LLaMA,极大降低 RAM 需求。
- **Database**: 捆绑 **SurrealDB (Embedded/Binary)**。
  - _理由_: 必须组件,体积小 (~50MB)。

### 2. 构建系统 (Build System)

- **PyInstaller**: 将 `python_backend` 编译为独立 `lumina_backend.exe`。
  - 自动处理 DLL 依赖(如 CUDA/Torch 仅保留 CPU 或轻量版)。
- **Electron-Builder**: 负责打包 Frontend + Backend EXE + SurrealDB + FFmpeg。
- **启动逻辑 (`main.ts`)**:
  - 检测生产环境 (`isPackaged`),自动 spawn `lumina_backend.exe` 而非 `python main.py`。
  - 自动管理子进程生命周期(退出时杀进程)。

## Compatibility

- **Non-Breaking**: 开发环境 (`npm run dev`) 保持不变。
- **Asset Management**: 模型下载逻辑需支持"从不下载"或"按需下载",避免安装包里塞入未使用模型。

## 预估体积

- Installer: < 300MB (如果是 CPU Torch) 或 ~800MB (如果包含基础 Torch 库)。
- 对比全本地版: ~5GB+。
