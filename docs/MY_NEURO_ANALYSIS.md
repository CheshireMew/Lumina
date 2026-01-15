# 🕵️‍♂️ My-Neuro 项目深度剖析报告

这是一个**教科书级别的 AI 桌面助理架构**。它不仅仅是一个脚本,而是一个微服务化的分布式系统。作者(morettt)非常注重**工程稳定性**和**用户体验(小白友好度)**。

核心架构图如下(基于代码推断):

```mermaid
graph TD
    User[用户/前端] <-->|HTTP| ASR[ASR 服务 (Port Default)]
    User <-->|HTTP| TTS[TTS 服务 (Port 5000)]
    User <-->|HTTP| RAG[记忆服务 (Port 8002)]
    User <-->|HTTP| BERT[意图识别 (Port 6007)]

    subgraph "ASR Service (asr_api.py)"
    FunASR[Paraformer 模型]
    Silero[Silero VAD]
    Punc[标点模型]
    end

    subgraph "TTS Service (GPT-SoVITS Bundle)"
    GSV[GPT-SoVITS API]
    note[独立进程/预打包环境]
    end

    subgraph "RAG Service (run_rag.py)"
    Embed[BGE-m3 模型]
    KB[记忆库.txt]
    Watchdog[文件监控]
    KB -.-> Watchdog
    Watchdog -->|自动重载| Embed
    end

    subgraph "Details"
    DL[Batch_Download.py] -->|下载管理| ASR
    DL -->|下载管理| RAG
    DL -->|显卡特判| TTS
    env[环境变量隔离]
    log[TeeOutput 双重日志]
    end
```

---

## 1. 核心模块详解

### 🔊 语音识别 (ASR) - `asr_api.py`

这是我们已经分析过的部分,最强的是**环境隔离**。

- **技术栈**: FunASR + Paraformer-Large + Silero VAD + CT-Transformer
- **亮点**: 并不是把所有模型一股脑塞进显存,而是按需加载。
- **杀手锏**: `os.environ['MODELSCOPE_CACHE'] = ...`。由于 ModelScope 和 HuggingFace 默认都会把模型下载到 C 盘的用户目录(难以清理、容易爆红),这个脚本强行劫持了环境变量,把模型锁死在项目目录里。

### 🗣️ 语音合成 (TTS) - `2.TTS.bat`

- **实现方式**: **外挂式**。
- 它没有在 Python 代码里 import GPT-SoVITS,而是直接启动了一个**预打包的 GPT-SoVITS 整合包**(`GPT-SoVITS-Bundle`)。
- **优势**: 彻底解耦。TTS 崩了不影响 ASR,而且不需要用户自己配 Python 环境(自带 runtime)。
- **细节**: 启动脚本里写死了角色 `neuro` 的参考音频和文本,保证了启动即用。

### 🧠 记忆增强 (RAG) - `run_rag.py`

- **端口**: 8002
- **技术栈**: BGE-M3 (当前最强的开源中英双语 Embedding 模型之一) + 纯文本数据库。
- **神来之笔**: **热重载 (Hot Reload)**。
  - 代码里引入了 `watchdog` 库监控 `记忆库.txt`。
  - 用户只要用记事本打开 `txt` 改几个字并保存,服务端的 `Observer` 瞬间检测到,自动重算 Embedding。这是极致的"小白友好"交互,不需要任何数据库操作界面。

### 👁️ 意图/情感分类 (BERT) - `omni_bert_api.py`

- **端口**: 6007
- **作用**: 一个简单的二分类器(Binary Classifier)。
- **标签**: `Vision` (视觉) 和 `core memory` (核心记忆)。
- **推测**: 用来判断用户的这句话是否需要调用"摄像头看一看"或者"查询核心设定",从而节省 Token。

---

## 2. 工程化细节(值得抄作业)

### 🛡️ 稳健的下载器 (`update.py` / `Batch_Download.py`)

这是最值得我们学习的地方。

- **断点续传**: 代码里检查了 HTTP Header `Range`。网断了?没关系,下次启动从断的地方继续下,不用重新跑。
- **镜像源轮询**: 准备了 `hk.gh-proxy.org`、`gh-proxy.org` 和 GitHub 原站三个源。一个挂了自动切下一个。
- **显卡检测**: 甚至写了逻辑去检测是不是 **RTX 50 系** 显卡(代码里有 `RTX 50` 的判断),如果是,下载特定的优化包。这更新速度太快了!

### 📝 双重日志 (TeeOutput)

- 所有服务都用了一个 `TeeOutput` 类。
- 它解决了"我看控制台想要颜色(高亮),但我存日志文件想要纯文本(去掉乱码)"的矛盾。很小的细节,但调试体验极佳。

### 🔄 自动备份 (`update.py`)

- 在更新版本时,它会自动把用户的 `记忆库.txt` 备份到临时文件,更新完整个文件夹后再拷回去。防止用户辛辛苦苦调教的记忆被覆盖。

---

## 💡 对 Lumina 的启示

1.  **RAG 热重载**: 我们的记忆系统目前可能需要重启生效。借鉴它的 `watchdog` 方案,可以让用户一边改设定文件,一边立即对话测试。
2.  **模型隔离**: 必须立刻实施 `os.environ` 劫持。这能解决我们之前担心的"模型下到哪里去了"的问题。
3.  **下载体验**: 引入 `Range` 断点续传。由于模型通常几百 MB,没有断点续传对用户简直是折磨。
