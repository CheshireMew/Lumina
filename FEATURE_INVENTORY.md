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
  - `tts_server.py`: Text-to-Speech (CosyVoice).
  - `tts_service.ts` & `audio_queue.ts`: Frontend TTS Streaming Layer (Added dynamic chunk buffering and low-latency playback).

## 📝 Documentation
- `MEM0_ANALYSIS.md`: Detailed analysis of `mem0` library and persistence issues.
- `MEMORY_RESEARCH_REPORT.md`: In-depth research on 4 similar projects (Lunasia, Live2D, NagaAgent, MoeChat) comparing their memory architectures.
