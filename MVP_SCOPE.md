# Lumina MVP Definition (Minimum Viable Product)

> Focus: Reliable, Low-Latency Conversation with Live2D Avatar.

## 1. Core User Loop (The "Must Haves")

- **Voice Interaction**:
  - [ ] **STT**: User speaks -> Accurate text transcription (SenseVoice).
  - [ ] **LLM**: Context-aware response (< 3s latency).
  - [ ] **TTS**: Natural voice output (GPT-SoVITS) synced with audio.
- **Visual Feedback**:
  - [ ] **Live2D**: Character renders, idles, and performs lip-sync to TTS.
  - [ ] **UI**: User sees chat bubble history.
- **Persistence**:
  - [ ] **Memory**: Conversation context persists across restarts (SurrealDB).

## 2. Critical Architecture (Enablers)

- **Backend Service**: `main.py` starts without error.
- **Frontend App**: Electron app launches and connects to `GET /network`.
- **Config**: Settings (API keys, paths) load correctly.

## 3. Excluded from MVP (Post-MVP)

- _Complex Plugins_ (Web Search, Home Assistant).
- _Long-term Memory Dreaming_ (The Gardener).
- _Multi-Character Switching_ (UI is there, but stability is lower priority).
- _Remote Process Isolation_ (Optimization, not functional req).

## 4. MVP Verification Plan

1.  **Startup Check**: One-click launch verify.
2.  **Ping Test**: Frontend <-> Backend connectivity.
3.  **Echo Test**: Speak -> STT logs text -> LLM replies -> TTS plays.
