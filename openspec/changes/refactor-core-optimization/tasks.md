# Tasks: Core Optimization & Technical Debt Cleanup

- [ ] **Dependency Audit**
  - [ ] Update `requirements.txt` with missing core libs (`surrealdb`, `pydantic`, `openai`, etc.).
  - [ ] Create `requirements-dev.txt` for testing libs.

- [ ] **Dead Code Cleanup (Graph Removal)**
  - [ ] Remove `add_knowledge_graph` method from `surreal_memory.py`.
  - [ ] Remove `add_insights` method from `surreal_memory.py`.
  - [ ] Remove `_resolve_entity` and related entity resolution logic.
  - [ ] Remove unused `networkx` imports if present.

- [ ] **Config Centralization**
  - [ ] Implement `ConfigManager` in `python_backend/app_config.py`.
  - [ ] Migrate `dreaming.py` to use `ConfigManager`.
  - [ ] Migrate `stt_server.py`/`tts_server.py` to use `ConfigManager`.

- [ ] **Memory Refactoring (Split God Class)**
  - [ ] Create package `python_backend/memory/`.
  - [ ] Extract `VectorStore` (Episodic Memory & HNSW logic) to `memory/vector_store.py`.
  - [ ] Extract `DBConnection` to `memory/connection.py`.
  - [ ] Refactor `SurrealMemory` to use these components.

- [ ] **Verification**
  - [ ] Verify `python main.py` starts successfully.
  - [ ] Verify Memory Extraction/Consolidation still works (using `test/test_soul_evo_deepseek.py`).
