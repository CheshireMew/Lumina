# Lumina Technical Reference Manual

> **Note**: This document is the "Deep Dive" source of truth for implementation details. It complements the `FEATURE_INVENTORY.md` (Architecture Overview).
> **Status**: Parts of this document describe historical storage design. For current runtime architecture, use `docs/ARCHITECTURE.md` and the live codebase.

---

## 1. Prompt Engineering System

Lumina uses a **Dynamic, Template-Driven** prompt system. We do not hardcode giant prompt strings in Python. Instead, we use `Jinja2` templates managed by `PromptManager`.

### 1.1 Architecture

```mermaid
graph TD
    A[Runtime State] -->|Dict| B(SoulManager)
    B -->|Identity/Mood/Time| C(SoulRenderer)
    C -->|Context| D(PromptManager)
    D -->|Load| E[Template: chat/system.yaml]
    D -->|Render| F[Final System Prompt]
```

### 1.2 Core Components

#### `PromptManager` (`python_backend/prompt_manager.py`)

- **Role**: Logic-less template engine.
- **Path**: Loads from `python_backend/prompts/`.
- **Format**: Supports `.yaml` (Structured) and `.jinja2` (Text).
- **Caching**: Templates are cached in memory for performance.

#### `SoulRenderer` (`services/soul/renderer.py`)

- **Role**: Pure function that transforms Raw State (Numbers, JSON) into Template Context (Strings).
- **Key Methods**:
  - `render()`: Generates the Base Persona (Static System Prompt).
  - `render_dynamic_context()`: Generates Real-Time context (Time, Mood, Energy).

### 1.3 Template Structure

We use a structured YAML approach (`prompts/chat/system.yaml`) to enforce strict instruction following.

```yaml
# Conceptual Structure of chat/system.yaml
role: |
  Name: {{ char_name }}
  Description: {{ description }}
  Personality Traits: {{ traits | join(', ') }}

style: |
  - Be concise.
  - Use emotive language appropriate for {{ mood }}.

constraints: |
  - NEVER output {{ forbidden_words }}.
  - Output format: JSON.
```

### 1.4 Dynamic Injection Logic

The final System Prompt is composed of layers provided by different modules via the `ContextProvider` interface.

1.  **Core Layer** (`SoulContextProvider`): Identity, Static Personality, Environment.
2.  **Plugin Layer** (e.g., `GalgameContextProvider`): Game State (Energy, Relationship).
3.  **Memory Layer** (`RAGContextProvider`): Retrieval.

This architecture ensures that `SoulManager` remains pure and core, while plugins like `Galgame` inject their specific logic dynamically.

### 1.5 Example: Soul State to Prompt

If `SoulManager` state is:

```json
{
  "mood_value": 0.8,
  "energy_level": 30
}
```

`SoulRenderer` transforms this to:

```python
context = {
  "mood_desc": "Elated",
  "energy_instruction": "You are tired. Speak in short, sleepy sentences."
}
```

The Template renders:

> "You are Elated. You are tired. Speak in short, sleepy sentences."

---

## 2. Memory System Internals

### 2.1 Storage Schema (SurrealDB)

We use a Graph-Vector hybrid model in SurrealDB.

- **Nodes**: `memory`, `entity`, `concept`.
- **Edges**: `relates_to`, `occured_at`.

#### `memory` Table

| Field        | Type         | Description                                   |
| :----------- | :----------- | :-------------------------------------------- |
| `content`    | string       | The text content.                             |
| `embedding`  | array<float> | 384-dim vector (all-MiniLM-L6-v2).            |
| `created_at` | datetime     | ISO 8601 timestamp.                           |
| `tags`       | list<string> | auto-generated tags.                          |
| `importance` | float        | 0.0 - 1.0 (Calculated via Recency/Relevance). |

### 2.2 The "Consolidation" Process

Memory isn't just storage; it's active.

1.  **Ingestion**: Chat text -> Vectorized -> Stored as Short-Term Memory.
2.  **Digestion** (Background Job):
    - `ConsolidationBatch` runs every X minutes.
    - Clusters recent memories.
    - Generates summary (LLM).
    - Writes to Long-Term Memory (Graph).
3.  **Refusal**: Use `NoOpDriver` if DB is offline, ensuring the bot can still talk (amnesiac mode).

---

## 3. Plugin Architecture

### 3.1 Unified Contract

插件协议已经收敛为一套固定模型：

- `manifest.yaml` 固定字段: `id`, `api_version`, `kind`, `capability`, `runtime_target`, `permissions`, `config_schema`, `provides`
- `plugin.py` 固定生命周期: `load(context)`, `enable()`, `disable()`, `unload()`, `health()`, `get_metadata()`

### 3.2 Capability Registry

系统内核不再按实现类做分发，而是只按 capability 做查找和选择。当前主干 capability 包括：

- `stt`
- `tts`
- `llm`
- `memory`
- `avatar`
- `tool.search`
- `chat.context`
- `chat.post_processor`

### 3.3 Config And Runtime State

- 写入意图只落到 `config.plugins.desired_state` 和 `config.plugins.selected_providers`
- 运行态只从 `plugin_state_aggregator` 读取
- 主进程插件由 `SystemPluginManager` 发本地状态
- Worker 插件由状态上报汇总后进入同一聚合视图

---

_To be continued: Audio Pipeline Details, Live2D Protocol..._
