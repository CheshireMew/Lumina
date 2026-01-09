# Tasks: Cleanup Legacy Architecture

- [x] **Refactor Model Loading** <!-- id: 0 -->
  - [x] Update `python_backend/model_manager.py` to support `load_embedding_model`. <!-- id: 1 -->
  - [x] Update `python_backend/main.py` to load model directly and inject into `SurrealMemory`. <!-- id: 2 -->
- [x] **Remove LiteMemory Usage** <!-- id: 3 -->
  - [x] Refactor `python_backend/memory_server.py` to remove `LiteMemory` init and fallbacks. <!-- id: 4 -->
  - [x] Refactor `python_backend/routers/soul.py` to remove `LiteMemory` usage in character switch. <!-- id: 5 -->
  - [x] Refactor `python_backend/routers/config.py` and `debug.py`. <!-- id: 6 -->
  - [x] Update `python_backend/routers/memory.py` to remove legacy fallbacks. <!-- id: 7 -->
- [x] **Archiving** <!-- id: 8 -->
  - [x] Create `python_backend/archive_legacy/` directory. <!-- id: 9 -->
  - [x] Move `lite_memory.py`, `time_indexed_memory.py`, `*_legacy.py` to archive. <!-- id: 10 -->
  - [x] Move `lite_memory_db/`, `memory_db/`, `lumina_memory.db` to archive. <!-- id: 11 -->
- [x] **Cleanup Dependencies** <!-- id: 12 -->
  - [x] Remove `qdrant-client` from `requirements.txt`. <!-- id: 13 -->
- [x] **Verification** <!-- id: 14 -->
  - [x] Restart backend and verify `/soul/switch_character` works. <!-- id: 15 -->
  - [x] Verify `SurrealMemory` still generates embeddings (using injected model). <!-- id: 16 -->
