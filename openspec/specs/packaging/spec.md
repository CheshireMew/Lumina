# packaging Specification

## Purpose
TBD - created by archiving change package-lite-distribution. Update Purpose after archive.
## 需求
### 需求：生产环境进程管理

Electron 主进程必须接管后端和数据库进程的生命周期。

#### 场景：生产环境启动

当 Electron 处于打包模式 (`apps.isPackaged === true`):

1. **不应** 尝试 spawn `python` 或 `pipenv` 命令。
2. **必须** 寻找相对于 resources 目录的 `lumina_backend.exe` (Windows) 或二进制文件。
3. **必须** 将必要的环境变量（如 `LUMINA_HOME`, `LITE_MODE`）传递给后端进程。
4. **必须** 能够定位绑定的辅助二进制文件 (`surreal.exe`, `ffmpeg.exe`) 并将其路径传给 Backend 配置。

### 需求：资源与依赖精简

为了构建轻量级安装包（目标 < 500MB），必须对依赖进行剪裁。

#### 场景：依赖精简

为减小安装包体积：

1. **移除** `torch` 的 CUDA 依赖库（如果是纯 CPU 推理版）。
2. **保留** `sherpa-onnx` 及其依赖。
3. **排除** `python_backend/models/*` 下的所有预下载大模型。
4. **排除** `python_backend/venv` 或 `node_modules` (后端部分)。

#### 场景：模型按需加载

后端检测到文件缺失时：

1. 默认模型（如 SenseVoice）应尝试从安装包内的 `assets` 加载，或者首次运行时自动下载（如果不包含）。
2. **建议**：在此 Lite 版本中，将 SenseVoice 量化模型 (~50MB) 直接打包进安装包。

