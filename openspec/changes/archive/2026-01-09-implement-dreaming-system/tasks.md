- [x] **Infrastructure & Schema** <!-- id: 0 -->
  - [x] Update `SurrealMemory` schema (`summary`, `insight`, `status`, `logs`). <!-- id: 1 -->
  - [x] Implement `mark_as_pending(ids)` in `SurrealMemory` (Touch-to-Dirt). <!-- id: 2 -->
  - [x] Implement `get_memories_for_dreaming()` (Fetch Raw + Pending). <!-- id: 3 -->
- [x] **Infrastructure - Dual Table Schema** <!-- id: 20 -->

  - [x] Create `conversation_log` table (Raw, No Vector). <!-- id: 21 -->
  - [x] Create `episodic_memory` table (Summary/Insight, Vector Index). <!-- id: 22 -->
  - [x] Migrate `SurrealMemory` methods to support dual tables. <!-- id: 23 -->

- [x] **Dreaming Split Implementation** <!-- id: 24 -->

  - [x] Implement `Extractor` logic in `dreaming.py` (Log -> Memory). <!-- id: 25 -->
  - [x] Implement `Consolidator` logic in `dreaming.py` (Memory + Memory -> Update/Delete). <!-- id: 26 -->
  - [x] Update `heartbeat_service` to trigger Extractor (fast) and Consolidator (slow/idle). <!-- id: 27 -->

- [x] **Integration** <!-- id: 9 -->
  - [x] Update `heartbeat_service.py` to trigger `dream_cycle` on idle. <!-- id: 10 -->
  - [x] Update `routers/memory.py` logging to set initial status `raw`. <!-- id: 11 -->
- [x] **Cleanup** <!-- id: 12 -->
  - [x] Archive `graph_curator.py` (Obsolete). <!-- id: 13 -->
  - [x] Clean up `entity` / `relation` tables in SurrealDB (Optional). <!-- id: 14 -->
- [x] **Verification** <!-- id: 15 -->
  - [x] Verify Raw logs are converted to Insights after digestion. <!-- id: 16 -->
  - [x] Verify "Touch-to-Dirt": Searching a memory marks it pending. <!-- id: 17 -->
  - [x] Verify Dreaming merges old pending memory with new context. <!-- id: 18 -->
