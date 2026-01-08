# Tasks: Cleanup Legacy Architecture

- [ ] **Refactor Model Loading** <!-- id: 0 -->
  - [ ] Update `python_backend/model_manager.py` to support `load_embedding_model`. <!-- id: 1 -->
  - [ ] Update `python_backend/main.py` to load model directly and inject into `SurrealMemory`. <!-- id: 2 -->
- [ ] **Remove LiteMemory Usage** <!-- id: 3 -->
  - [ ] Refactor `python_backend/memory_server.py` to remove `LiteMemory` init and fallbacks. <!-- id: 4 -->
  - [ ] Refactor `python_backend/routers/soul.py` to remove `LiteMemory` usage in character switch. <!-- id: 5 -->
  - [ ] Refactor `python_backend/routers/config.py` and `debug.py`. <!-- id: 6 -->
  - [ ] Update `python_backend/routers/memory.py` to remove legacy fallbacks. <!-- id: 7 -->
- [ ] **Archiving** <!-- id: 8 -->
  - [ ] Create `python_backend/archive_legacy/` directory. <!-- id: 9 -->
  - [ ] Move `lite_memory.py`, `time_indexed_memory.py`, `*_legacy.py` to archive. <!-- id: 10 -->
  - [ ] Move `lite_memory_db/`, `memory_db/`, `lumina_memory.db` to archive. <!-- id: 11 -->
- [ ] **Cleanup Dependencies** <!-- id: 12 -->
  - [ ] Remove `qdrant-client` from `requirements.txt`. <!-- id: 13 -->
- [ ] **Verification** <!-- id: 14 -->
  - [ ] Restart backend and verify `/soul/switch_character` works. <!-- id: 15 -->
  - [ ] Verify `SurrealMemory` still generates embeddings (using injected model). <!-- id: 16 -->
