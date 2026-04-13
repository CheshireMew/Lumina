# Lumina 架构愿景 (Alliance)

> **版本**: 2026-01-24 (Post-Refactor Reflection)
> **状态**: 远期规划文档
> **目的**: 记录从 v1.0 迈向 v3.0 的演进路径，防止迷失技术方向。

---

## 🏆 总体路线图

| 阶段     | 代号              | 核心目标    | 关键特征                                       |
| :------- | :---------------- | :---------- | :--------------------------------------------- |
| **v1.0** | **Foundation**    | ✅ **稳健** | 模块化、不轻易崩溃、可观测、标准协议 (LIPP)。  |
| **v1.1** | **Invincibility** | ⏳ **自愈** | Supervisor 重启策略、故障降级、看门狗增强。    |
| **v1.5** | **Performance**   | ⚡ **极速** | 二进制流、共享内存零拷贝、CPU亲和性调度。      |
| **v2.0** | **Cognitive**     | 🧠 **懂你** | 上下文感知 STT、长期记忆整合、主动式任务规划。 |
| **v3.0** | **Swarm**         | 🌐 **无界** | 分布式节点、零配置组网、云边协同。             |

---

## 🛠️ v1.5 工程化瓶颈与解法

### 1. 传输效率 (The "Base64" Tax)

- **痛点**: 目前 Worker 通信依赖 JSON + Base64，增加了 33% 体积且消耗大量 CPU 进行序列化。
- **解法 A (Binary LIPP)**: 升级 WebSocket 协议，支持混合帧（JSON Header + Binary Body）。
- **解法 B (Shared Memory)**: 利用 Python `multiprocessing.shared_memory`在 Main/Worker 间零拷贝传输音频环形缓冲区 (Ring Buffer)。延迟可降至微秒级。

### 2. 僵尸防御 (Self-Healing)

- **痛点**: 目前只有被动报警 (`Worker OFFLINE`)，没有主动恢复。
- **解法 (Supervisor)**:
  - `ProcessManager` 升级为 Supervisor。
  - 策略: `Restart=on-failure`, `MaxRetries=3`, `Backoff=Exponential`。
  - **Fallback**: GPU Worker 连续崩溃 -> 自动拉起 CPU Worker 或 Cloud Driver。

---

## 🧠 v2.0 认知架构升级

### 3. 上下文孤岛 (Context Silos)

- **痛点**: STT 听不懂专有名词，因为它不知道 LLM 刚才聊了什么，也不知道安装了哪些插件。
- **解法 (Context-Aware Streaming)**:
  - Main Process 维护一棵 **"Live Context Tree"**。
  - 实时将热词 (Hotwords) 推送给 STT Worker（例如：加载了 "Jellyfin" 插件，STT 权重中 "Jellyfin" 自动调高）。

### 4. 主动性 (Proactive Agency)

- **痛点**: 只有用户说话系统才动 (Reactive)。
- **解法 (ECA Engine)**:
  - 引入 **Event-Condition-Action** 引擎。
  - 允许插件注册后台触发器 (e.g., `on(Event.CPU_TEMP > 80) -> run(CoolingPolicy)` )。
  - 这需要将事件总线从单纯的消息传递升级为**状态机驱动**。

---

## 🔬 关键技术预研 (R&D)

1.  **Arrow / Ray**: 考察是否引入 Ray 作为下一代进程管理底座（解决分布式 + 共享内存）。
2.  **OpenTelemetry**: 当链路超过 3 层时（Main -> Worker -> Plugin -> External API），必须上全链路追踪。
3.  **Local LLM Fine-tuning**: 探索利用用户日常对话数据，在本地轻量微调 STT/LLM 的可能性（Lora）。

---

> **架构师寄语**:
> 只要基础架构还是 v1.0，任何“智能”都像是建立在沙堆上的城堡。
> **下一步首要任务：v1.1 Invincibility (不死之身)。**

一、 现有架构的隐形瓶颈 (Engineering Gaps)
虽然我们实现了模块化，但在高性能和高可用方面还有硬伤。

1. "Base64" 的诅咒 (传输效率)
   现状: 目前 LIPP 协议和 Worker 通信主要依赖 JSON + Base64。
   问题: Base64 会增加 33% 的数据体积，且 JSON 解析/序列化在 Python 中是 CPU 密集型的。对于 24/7 的实时音频流，这是巨大的算力浪费。
   优化方向:
   二进制协议: WebSocket 支持 Binary Frame。LIPP 应该支持 Header (JSON) + Body (Binary) 的混合传输模式。（v1.5 已采纳）
   共享内存 (Shared Memory): [Optional/Local Optimization] 仅当 Binary Protocol 仍无法满足延迟要求时的终极手段。技术复杂度高，暂缓实施。
2. "僵尸" 防御 (自愈能力 Supervisor)
   现状:
   PluginRegistry
   有 Watchdog，发现 Worker 掉线会报错 🚨 Worker OFFLINE。
   问题: 然后呢？目前系统只会看着它死掉。Main Process 没有实现 Supervisor (监管者) 策略。如果 STT Worker 崩溃（比如 CUDA OOM），整个语音交互就断了，用户必须手动重启。
   优化方向:
   自动重启策略: 在
   ProcessManager
   实现 RestartPolicy (Always, On-Failure)。
   备用降级: STT (GPU) 挂了，自动降级为 STT (Cloud API) 或 STT (CPU)。
   二、 认知架构的缺失 (Cognitive Gaps)
   这是 Lumina 与简单的 "Chatbot" 的本质区别。目前的架构各组件还是割裂的。

3. 上下文孤岛 (Context Silos)
   现状:
   STT 负责听（只听音素）。
   LLM 负责想（只看文本）。
   问题: STT 经常听错专有名词（比如把 "Lumina" 听成 "Luminous"），因为它不知道 LLM 刚才聊了什么，也不知道系统里安装了什么插件名。
   优化方向: Context-Aware Streaming。Main Process 应该把当前的“关键词热词表 (Hotwords)”（来自当前对话上下文 + 插件列表）实时推给 STT Worker。这就实现了“带着脑子听”。
4. 缺乏主动性 (Reactive vs Proactive)
   现状: 架构是 Request-Response 模型的。用户不说话，系统就永远在休眠。
   问题: 真正的助理应该能主动工作。例如：“监测到 CPU 温度过高，我已自动关闭了后台的游戏进程。”
   优化方向: 引入 Event-Condition-Action (ECA) 引擎 或 Task Scheduler。允许插件注册“后台触发器”（不仅仅是响应用户指令）。

### 5. 重型任务 (Heavy Lifting)

- **痛点**: `Dreaming` (记忆整理) 等重型 ETL 任务目前在主循环中运行，拖慢系统响应。
- **解法 (Subconscious Service)**:
  - 引入 **Job Queue / Task Scheduler** (潜意识)。
  - 专职负责异步任务：记忆整理、数据备份、日志分析。
  - 特性：低优先级、资源限制、断点续传。

### 6. 人格演化 (Personality Evolution)

- **痛点**: `Soul Evolution` 逻辑硬编码在插件中，缺乏统一的心理学模型支持。
- **解法 (Psychology Engine)**:
  - 引入 **Personality Service**。
  - 提供标准心理模型 (Big 5, PAD) 的状态管理和演化算法。
  - 插件只需提交 "Experience"，引擎负责计算 "Growth"。

---

## 🔬 关键技术预研 (R&D)

1.  **Arrow / Ray**: 考察是否引入 Ray 作为下一代进程管理底座（解决分布式 + 共享内存）。
2.  **OpenTelemetry**: 当链路超过 3 层时（Main -> Worker -> Plugin -> External API），必须上全链路追踪。
3.  **Local LLM Fine-tuning**: 探索利用用户日常对话数据，在本地轻量微调 STT/LLM 的可能性（Lora）。

---

> v1.0 是骨架，v1.1 是肌肉 (自愈)，v1.5 是神经 (极速)，v2.0 是大脑 (ECA)。
> 接下来的 **v2.5 (Subconscious & Psych)** 将赋予它“灵魂”。

---

## 🗿 概念定义 (Conceptual Definitions)

### Dreaming System (The Hippocampus)

Dreaming System 不应仅作为一个“插件”，它是 AI 的**海马体**。

- **Extract (提取)**: 从高频对话流中提取事实。
- **Consolidate (整合)**: 将碎片化信息合并为长期语义记忆。
- **Forget (遗忘)**: 垃圾回收，丢弃低价值信息。
  **架构定位**: 它是 AI 的“肾脏”（代谢系统），应运行在后台的 `Subconscious Service` (Job Pipeline) 中，而非主线程。

### Tri-Core Cognitive Architecture (v2.5)

未来的认知核心将由三部分组成：

1.  **ECA Engine (Reflex)**: 神经反射 (Prefrontal Cortex)。解决 "When to act"。
2.  **Job Service (Metabolism)**: 新陈代谢 (Subconscious)。解决重型任务 (Dreaming)。
3.  **Psych Service (Self)**: 自我意识 (Soul)。解决人格演化 (Evolution)。
