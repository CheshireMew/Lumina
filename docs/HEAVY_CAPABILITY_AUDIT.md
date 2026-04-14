# 重依赖归属冻结表

这份表对应 `HEAVY_CAPABILITY_DECOUPLING_PLAN.md` 的 Phase 0，用来冻结当前事实，不在拆包过程中继续猜。

## 映射表

| 库 | 真实导入点 | 归属能力 | 第一次导入时机 | 可懒加载 | 可独立打包 | 结论 |
| --- | --- | --- | --- | --- | --- | --- |
| `live2d` 资源与 Cubism runtime | `app/renderer/plugins/avatar/live2d/*`、`python_backend/core/api/app_factory.py`、`python_backend/packaging/backend.spec` | `live2d-assets` | 主界面渲染前后会接触，但本质是可选前端资源 | 是 | 是 | 从主包静态资源中拆出，主程序只认资源 contract |
| `torch` | `python_backend/model_manager.py`、`python_backend/plugins/extensions/voiceauth_sherpa/drivers/voiceauth/sherpa_cam_driver.py` | `vision-runtime`（记忆向量推理）与 `voiceprint-runtime`（声纹） | 都不是主启动导入，分别在记忆向量编码和声纹驱动加载时首次导入 | 是 | 是 | 从默认依赖移出；核心链路只保留降级能力 |
| `transformers` | 通过 `sentence_transformers` 进入 `python_backend/model_manager.py` | `vision-runtime` | 记忆检索真正需要向量编码时才导入 | 是 | 是 | 不再属于默认主包 |
| `cv2` | 代码中没有生产导入，当前只在旧构建产物依赖树里出现 | 无 | 不该进入生产链路 | 不需要 | 不需要 | 直接从主包删除，不做能力包 |
| `llvmlite` | 代码中没有生产导入，当前只在旧构建产物依赖树里出现 | 无 | 不该进入生产链路 | 不需要 | 不需要 | 直接从主包删除，不做能力包 |

## 启动链断点

### 主程序默认必须保留

- Electron 主壳
- `lumina_backend.exe core` 对应的 core runtime
- 配置、路由、插件协议、worker 调度
- 轻量静态资源与普通头像资源

### 当前错误绑定

- `public/live2d` 被前端静态资源和后端静态挂载双重假定
- `torch / transformers / sentence-transformers` 仍在默认 requirements 中，导致主环境天然背上重推理链
- STT/TTS worker 在 `python_backend/core/bootstrap/post_startup.py` 默认预热，重新把可选能力带回主启动路径

### 删除名单

- 主包中的 `dist/live2d/**/*`
- 主包中的 `dist/libs/live2dcubismcore.min.js`
- 主包默认 Python 依赖中的 `torch`、`transformers`、`torchvision`、`sentence-transformers`
- 任何仅因本机环境污染而被 PyInstaller 顺手带入的 `cv2`、`llvmlite`

## 白名单

- `core-runtime`
- 非 Live2D 的普通前端资源
- STT/TTS 的路由 contract 与按需启动入口
- 记忆系统的全文检索降级链路

## 归属结论

- `live2d-assets`：资源包，前端动态加载，缺失时只显示轻占位。
- `stt-runtime`：运行时包，按需启动，不再默认预热。
- `tts-runtime`：运行时包，按需启动。
- `voiceprint-runtime`：可选运行时包，未安装时只显示 unavailable。
- `vision-runtime`：承接向量编码与其他可选推理链；未安装时核心系统退化到全文检索。

## Phase 2-10 收口状态

`config/capability-packages.json` 是能力包唯一 contract。主程序通过 `CapabilityPackageRegistry` 识别安装状态、版本、入口、资源目录和缺失文件；业务代码不再直接猜 `public/live2d`、`dist_backend`、`torch` 或 worker 路径。

构建产物固定为：

- `dist_backend/lumina_backend`：主 core runtime，只保留核心后端、路由、插件协议、worker 调度和轻量代理。
- `dist_backend/packages/core-runtime`：core 元数据包。
- `dist_backend/packages/live2d-assets`：Live2D 模型和 Cubism runtime。
- `dist_backend/packages/stt-runtime`：STT worker、STT 插件、STT 依赖和 `data/models`。
- `dist_backend/packages/tts-runtime`：TTS worker 和 TTS 插件。
- `dist_backend/packages/voiceprint-runtime`：声纹插件、声纹驱动和声纹依赖清单。
- `dist_backend/packages/vision-runtime`：视觉/推理依赖清单；当前没有生产视觉驱动，`cv2` 与 `llvmlite` 不做包。

最终校验已加入 `npm run verify-capabilities`。它会检查所有能力包的 `manifest.json`、`version.json`、`hashes.json`，并阻止 `torch`、`transformers`、`cv2`、`llvmlite`、`sherpa_onnx`、`faster_whisper`、`edge_tts` 以及 STT/TTS/Vision 实现源码重新进入 core runtime。
