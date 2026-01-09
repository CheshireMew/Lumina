- [ ] **Specs definition** <!-- id: 0 -->

  - [ ] Draft `specs/soul/spec.md` for Split System Prompt requirements. <!-- id: 1 -->

- [ ] **Python Backend Implementation** <!-- id: 2 -->

  - [ ] Implement `SoulManager.render_static_prompt` (Identity/Traits/Values). <!-- id: 3 -->
  - [ ] Implement `SoulManager.render_dynamic_instruction` (Mood/Time/Energy). <!-- id: 4 -->
  - [ ] Update `routers/soul.py` to return both fields. <!-- id: 5 -->

- [ ] **Frontend Implementation** <!-- id: 9 -->

  - [ ] Update `App.tsx` message construction: `[Static] -> [History] -> [Dynamic]`. <!-- id: 10 -->

- [x] **Verification** <!-- id: 6 -->

  - [x] Unit Test `python_backend/test_prompt_split.py`. <!-- id: 7 -->
  - [x] Script `python_backend/test_scenario_mixing.py` (Active/Proactive Simulation). <!-- id: 12 -->
  - [x] Manual Verification via App Chat Log. <!-- id: 8 -->

- [x] **Debugging** <!-- id: 13 -->
  - [x] Investigate `lumina_default` fallback issue. <!-- id: 14 -->
  - [x] Fix Proactive Memory Injection (Header Wrapping Issue). <!-- id: 15 -->
  - [x] Optimization <!-- id: 16 -->
    - [x] Implement Adaptive/Gradient Threshold for Memory Search. <!-- id: 17 -->
    - [x] Optimize Keyword Search for Chinese (Use `CONTAINS`). <!-- id: 18 -->
  - [ ] **Debugging** <!-- id: 19 -->
    - [ ] Investigate Extractor Count Mismatch (Count=20, Fetched=5). <!-- id: 20 -->
    - [x] Fix Proactive Chat "Random Inspiration" (Source/Limit). <!-- id: 21 -->
