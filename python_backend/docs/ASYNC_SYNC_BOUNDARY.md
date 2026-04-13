# Lumina 异步/同步边界规范

> **版本**: v1.0
> **日期**: 2026-01-24
> **目的**: 明确项目中异步与同步代码的使用边界和最佳实践

---

## 📊 架构层次总览

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI / Uvicorn                        │ ← 纯异步
├─────────────────────────────────────────────────────────────┤
│                    Routers / Endpoints                      │ ← 纯异步
├─────────────────────────────────────────────────────────────┤
│                    Services Layer                           │ ← 混合 (见下)
├─────────────────────────────────────────────────────────────┤
│                    Drivers / Plugins                        │ ← 主要同步
├─────────────────────────────────────────────────────────────┤
│                    I/O (Audio, File, Network)               │ ← 阻塞同步
└─────────────────────────────────────────────────────────────┘
```

---

## ✅ 纯异步层 (Async-Only)

以下层**必须**使用 `async def`，禁止阻塞调用：

| 层               | 组件                                                | 说明               |
| ---------------- | --------------------------------------------------- | ------------------ |
| **HTTP 层**      | `routers/*.py`                                      | FastAPI 路由处理器 |
| **WebSocket**    | `worker_control_hub.py`, `worker_control_client.py` | 实时通信           |
| **生命周期**     | `lifecycle.py`, `shutdown_manager.py`               | 应用启动/关闭      |
| **Bootstrapper** | `core/bootstrap/*.py`                               | 启动阶段初始化     |
| **事件总线**     | `core/events/bus.py`                                | 事件发布/订阅      |
| **协调服务**     | `reconciliation_service.py`                         | 控制循环           |
| **状态聚合**     | `plugin_state_aggregator.py`                        | 状态合并           |

### 规则

```python
# ✅ 正确
async def handle_request(request: Request):
    result = await some_async_operation()
    return result

# ❌ 错误 - 在异步上下文中阻塞
async def handle_request(request: Request):
    result = time.sleep(5)  # 阻塞整个事件循环！
    return result
```

---

## ⚠️ 混合层 (需要桥接)

以下服务**内部逻辑异步**，但调用**同步底层**：

| 服务                | 异步方法                           | 同步调用        | 桥接方式            |
| ------------------- | ---------------------------------- | --------------- | ------------------- |
| `STTPluginManager`  | `activate()`, `register_drivers()` | `driver.load()` | `run_in_executor`   |
| `TTSPluginManager`  | `activate()`, `register_drivers()` | `driver.load()` | `run_in_executor`   |
| `PluginController`  | `install_plugin()`                 | 文件 I/O        | `asyncio.to_thread` |
| `MemoryService`     | `add()`, `search()`                | 向量编码        | `asyncio.to_thread` |
| `VoiceprintManager` | `identify()`                       | 嵌入提取        | `run_in_executor`   |

### 正确桥接方式

```python
# 方式 1: asyncio.to_thread (Python 3.9+, 推荐)
async def install_plugin(self, file):
    await asyncio.to_thread(self._save_file_sync, file)

# 方式 2: run_in_executor (更细粒度控制)
async def activate(self, driver_id: str):
    loop = asyncio.get_event_loop()
    await loop.run_in_executor(None, driver.load)

# 方式 3: 专用线程池 (高吞吐场景)
from concurrent.futures import ThreadPoolExecutor
IO_POOL = ThreadPoolExecutor(max_workers=4, thread_name_prefix="io_")

async def process_audio(self, data):
    loop = asyncio.get_event_loop()
    result = await loop.run_in_executor(IO_POOL, self._cpu_intensive, data)
```

---

## 🔒 纯同步层 (Sync-Only)

以下组件**必须保持同步**，不应引入异步：

| 层           | 组件                  | 原因                       |
| ------------ | --------------------- | -------------------------- |
| **ML 推理**  | STT/TTS Drivers       | PyTorch/ONNX 是同步的      |
| **音频处理** | AudioManager, VAD     | 低延迟要求，运行在独立线程 |
| **文件 I/O** | Config 读写           | 简单操作，无需异步         |
| **嵌入计算** | Voiceprint, Embedding | CPU 密集型                 |
| **进程管理** | subprocess 调用       | 系统级操作                 |

### 规则

```python
# ✅ 正确 - 保持同步，让上层决定如何调用
class WhisperDriver:
    def transcribe(self, audio: bytes) -> str:
        # 同步阻塞操作
        return self.model.transcribe(audio)

# 上层服务负责桥接
async def transcribe_async(self, audio: bytes):
    loop = asyncio.get_event_loop()
    return await loop.run_in_executor(None, self.driver.transcribe, audio)
```

---

## 🧵 Threading 使用场景

| 场景           | 组件                    | 原因                   |
| -------------- | ----------------------- | ---------------------- |
| **音频回调**   | `bootstrap/services.py` | PyAudio 回调在独立线程 |
| **进程输出流** | `process_manager.py`    | 读取子进程 stdout      |
| **后台任务**   | `global_ticker.py`      | 定时任务不依赖事件循环 |

```python
# 示例: 音频回调 -> 异步事件
def on_speech_end(audio_data):
    def _transcribe():
        result = stt_manager.transcribe(audio_data)  # 同步
        stt_globals.message_queue.put({"type": "transcription", "text": result})

    # 在独立线程执行，不阻塞音频回调
    threading.Thread(target=_transcribe).start()
```

---

## 📋 当前 `asyncio.to_thread` 使用统计

| 文件                            | 行号 | 用途         |
| ------------------------------- | ---- | ------------ |
| `services/plugin/controller.py` | 254  | 保存上传文件 |
| `services/plugin/controller.py` | 257  | 解压插件     |
| `services/plugin/controller.py` | 271  | 重载插件     |
| `routers/plugins.py`            | 100  | 重载插件     |
| `memory/core.py`                | 285  | 向量编码     |

---

## 📋 当前 `run_in_executor` 使用统计

| 文件                                | 行号     | 用途            |
| ----------------------------------- | -------- | --------------- |
| `services/stt_manager.py`           | 192      | 加载 STT Driver |
| `capabilities/stt/manager.py`       | 187      | 加载 STT Driver |
| `capabilities/stt/__init__.py`      | 99       | 转写音频        |
| `capabilities/stt/routes.py`        | 350      | 提取声纹嵌入    |
| `plugins/.../voiceprint/manager.py` | 149, 324 | 声纹识别        |
| `core/isolation/proxy.py`           | 296      | 进程间通信      |

---

## 🚫 禁止模式

### 1. 在异步函数中直接调用阻塞 I/O

```python
# ❌ 错误
async def read_config():
    with open("config.yaml") as f:  # 阻塞！
        return yaml.load(f)

# ✅ 正确
async def read_config():
    return await asyncio.to_thread(_read_config_sync)
```

### 2. 在同步回调中调用 asyncio

```python
# ❌ 错误 - 同步上下文中调用 asyncio
def on_audio_callback(data):
    asyncio.run(process_audio(data))  # 创建新事件循环！

# ✅ 正确 - 使用消息队列
def on_audio_callback(data):
    message_queue.put({"type": "audio", "data": data})
```

### 3. 混合 Thread 和 asyncio 不当

```python
# ❌ 错误 - 线程中直接调用 coroutine
def worker_thread():
    await some_async_fn()  # SyntaxError

# ✅ 正确 - 使用 run_coroutine_threadsafe
def worker_thread():
    future = asyncio.run_coroutine_threadsafe(some_async_fn(), main_loop)
    result = future.result()
```

---

## ✅ 最佳实践总结

| 原则         | 说明                                             |
| ------------ | ------------------------------------------------ |
| **层次分离** | 上层异步，底层同步，中间桥接                     |
| **桥接统一** | 优先 `asyncio.to_thread`，其次 `run_in_executor` |
| **线程隔离** | 音频、进程输出使用独立线程                       |
| **队列通信** | 线程与异步间用队列+轮询                          |
| **文档标注** | 同步函数标注 `# Sync`, 阻塞操作标注 `# Blocking` |

---

## 📝 后续优化

1. **添加类型注解**: 明确标注同步/异步函数
2. **统一桥接工具**: 创建 `core/async_bridge.py` 封装常用模式
3. **性能监控**: 添加桥接调用耗时 Metric
