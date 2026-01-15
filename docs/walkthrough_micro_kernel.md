# Micro-Kernel Architecture Migration Walkthrough

## Overview

We have successfully implemented the foundational **Micro-Kernel Architecture** for Lumina. This shifts the system from a monolithic design to a modular, plugin-based approach.

### Key Changes

1.  **Plugin Infrastructure**:

    - `PluginManager`: Handles discovery and loading of plugins.
    - `BasePlugin` Interfaces: Standardized `ASRPlugin` and `TTSPlugin` protocols.
    - `python_backend/plugins/`: New directory for all kernel extensions.

2.  **Core Drivers (Plugins)**:

    - **SenseVoice (ASR)**: Migrated core logic to `plugins/drivers/stt/sensevoice/`.
    - **EdgeTTS (TTS)**: Migrated core logic to `plugins/drivers/tts/edge_tts/`.

3.  **Server Integration**:

    - `stt_server.py` and `tts_server.py` have been updated to support dynamic plugin loading.
    - Legacy logic is preserved for safety, but can be bypassed by configuration.

4.  **MCP Host (Preview)**:
    - Basic `MCPManager` implemented to support future "Skills" (e.g., Web Search).

## How to Verify & Switch

### 1. Verify Plugins Loaded

Run the verification script to confirm the system detects the new plugins:

```powershell
python python_backend/test_plugins.py
```

**Expected Output:**

```text
[PASS] SenseVoice plugin found: stt:sensevoice v1.0.0
[PASS] EdgeTTS plugin found: tts:edge_tts v1.0.0
```

### 2. Switch STT to Plugin Mode

To use the new modular SenseVoice driver instead of the hardcoded one:

1.  Open `python_backend/app_config.py` (or `stt_config.json` if generated).
2.  Set the STT model to use the `plugin:` prefix.

**Example `stt_config.json`:**

```json
{
  "model": "plugin:sensevoice"
}
```

_Restart Lumina. The logs should show `Plugin ASR Engine (stt:sensevoice) loaded successfully`._

### 3. Switch TTS to Plugin Mode

To use the new modular EdgeTTS driver:

1.  In your frontend or API request, set the `engine` parameter to `plugin:edge_tts` (or `tts:edge_tts`).

**Example API Request:**

```json
POST /tts/synthesize
{
  "text": "Hello world",
  "engine": "plugin:edge_tts",
  "voice": "zh-CN-XiaoxiaoNeural"
}
```

## Next Steps

- **MCP Integration**: Move Web Search to an MCP Skill.
- **Cleanup**: Once plugins are proven stable, remove the legacy "hardcoded" logic from `stt_server.py` and `tts_server.py`.
