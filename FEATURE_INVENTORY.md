# Feature Inventory

## 🧠 Memory System (LiteMemory V2)
- **Status**: ✅ Operational / Optimized
- **Architecture Doc**: [LUMINA_MEMORY_ARCHITECTURE_V2.md](LUMINA_MEMORY_ARCHITECTURE_V2.md)
- **Components**:
  - `lite_memory.py`: Custom Dual-Layer Logic Engine (Replaced `mem0`).
  - `fact_extractor.py`: Dedicated User Fact Extraction.
  - `memory_consolidator.py`: LLM-based Background Consolidation.
  - `rebuild_db.py`: Database Migration Tool.
- **Models**:
  - LLM: DeepSeek (via OpenAI-compatible API).
  - Embeddings: `paraphrase-multilingual-MiniLM-L12-v2` (384d, Local).
- **Storage**:
  - Vector: Qdrant (Local `./lite_memory_db`) - Index Only.
  - Persistence: JSONL (`./memory_backups/*.jsonl`) - Single Source of Truth.

## 🗣️ Voice System
- **Status**: ✅ Operational
- **Components**:
  - `stt_server.py`: Speech-to-Text (FunASR/SenseVoice).
  - `tts_server.py`: Text-to-Speech (CosyVoice & GPT-SoVITS).
    - **Optimization**: Implemented "Raw Stream Pipe" architecture. Requests PCM Stream from GPT-SoVITS and transcodes to AAC via local FFmpeg pipe for zero-latency MSE compatibility.
    - **Performance**: Added TTFB (Time To First Byte) & Chunk monitoring logs.
    - **Emotion Control**: Edge TTS 不支持情感样式（代码中 SSML 逻辑为接口预留）；GPT-SoVITS 通过参考音频（`assets/emotion_audio/`）实现情感克隆。
  - `tts_service.ts` & `audio_queue.ts`: Frontend TTS Streaming Layer (Added dynamic chunk buffering and low-latency playback).

## 🎨 Live2D / Character System
- **Status**: ✅ Operational / Optimized
- **Components**:
  - `Live2DViewer.tsx`: Core model renderer.
  - `emotion_map.json`: Maps linguistic emotions (e.g. `happy`, `开心`) to model motion groups.
- **Features**:
  - **Motion Triggers**: LLM-driven `[emotion]` tags trigger animations (Priority 3 Force).
  - **Quiet Mode**: Custom 15s Idle Timer disables internal auto-motion to prevent interruptions.
  - **Tag Hiding**: `App.tsx` & `ChatBubble.tsx` strip `[tags]` from UI/TTS output.
  - **Multi-Character**: Support for multiple profiles, each with custom prompts (auto-injected system instructions).
- **Debugging**:
  - Enhanced emotion detection logging in `App.tsx` (processEmotions function).
  - Detailed logs for: buffer content, tag matches, emotion mapping, trigger status.
  - Support for Chinese parentheses「)」in emotion tags.
  - Test script: `test/emotion_test.ts`.
  - Debug guide: `.gemini/antigravity/brain/.../emotion_debug_guide.md`.


## 📝 Documentation
- `MEM0_ANALYSIS.md`: Detailed analysis of `mem0` library and persistence issues.
- `MEMORY_RESEARCH_REPORT.md`: In-depth research on 4 similar projects (Lunasia, Live2D, NagaAgent, MoeChat) comparing their memory architectures.

- **Voice Input**: Updated microphone icon to circular design with visual states (Ready/Listening/Thinking).
- **UI Design**: Applied flat layered design to Voice Input icon (Outer Ring + Inner Circle).
- **UI Design**: Simplified Voice Input icon to pure Glyph style (No background ring/circle).
- **UI Design**: Added Frosted Glass effect background to Voice Input icon.
