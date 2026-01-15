# Tasks: Package Lite Distribution

## Phase 1: Configuration & Profile

- [ ] 创建 `build_config.py` 或修改 `config.py` 以支持 `LITE_MODE` 标志。
- [ ] 验证 `SenseVoice` 和 `Edge TTS` 在纯净 Python 环境下的依赖最小化。

## Phase 2: Backend Compilation (PyInstaller)

- [ ] 创建 `backend_launcher.py`: 统一入口,根据参数 (`--service=stt|tts|memory`) 启动对应服务,方便打包为一个 EXE。
- [ ] 创建 `python_backend/hook-*.py` 钩子文件以正确处理库依赖(如 `sherpa_onnx`, `fastapi`, `numpy`)。
- [ ] 编写 `build_backend.spec` 能够生成单文件或单目录的 `lumina_backend`。
- [ ] 验证编译后的 Backend 能正常启动 `FastAPI` 和连接 `SurrealDB`。

## Phase 3: Electron Integration

- [ ] 修改 `app/main/main.ts` 以识别 `app.isPackaged` 并调用 `.exe`。
- [ ] 配置 `electron-builder.yml` 或 `package.json` 以包含外部二进制文件 (`lumina_backend.exe`, `surreal.exe`, `ffmpeg.exe`)。
- [ ] 实现子进程的优雅退出(防止僵尸进程)。

## Phase 4: Installer & Validation

- [ ] 运行构建命令生成 `Lumina-Setup-0.1.0.exe`。
- [ ] 在干净的虚拟机/沙盒中测试安装和运行。
- [ ] 验证 STT/TTS 在无 Python 环境下的功能。
