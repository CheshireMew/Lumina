# Lumina Logging Standard

## Language

**All log messages must be in English.**

## Log Levels

| Level     | Usage                                            |
| --------- | ------------------------------------------------ |
| `DEBUG`   | Verbose internal state, driver loading details   |
| `INFO`    | Startup, important state changes, plugin loading |
| `WARNING` | Non-fatal issues, degraded functionality         |
| `ERROR`   | Failures requiring attention                     |

## Emoji Rules

Use emojis **sparingly** at the start of INFO-level messages for visual scanning.

| Emoji | Meaning       | Example                             |
| ----- | ------------- | ----------------------------------- |
| ✅    | Success       | `✅ Plugin loaded: {id}`            |
| ❌    | Failure       | `❌ Plugin load failed: {id}`       |
| 🚀    | Startup       | `🚀 Starting server on port {port}` |
| 🔌    | Plugin/Driver | `🔌 Plugin unloaded: {id}`          |
| ⚠️    | Warning       | `⚠️ Service degraded`               |
| 📂    | File/IO       | `📂 Scanning directory: {path}`     |
| 🧩    | Discovery     | `🧩 Discovered {n} plugins`         |
| 💤    | Disabled/Skip | `💤 Plugin disabled, skipping`      |
| ✨    | Completion    | `✨ Initialization complete`        |

**Rules:**

- DEBUG/ERROR: No emojis
- WARNING: Optional ⚠️
- INFO: Optional relevant emoji
- Never use emojis in exception messages

## Format

```python
# Good
logger.info(f"✅ Plugin loaded: {plugin_id}")
logger.error(f"Failed to load plugin {plugin_id}: {e}")

# Bad
logger.info(f"✅ 插件已加载: {plugin_id}")  # Chinese
logger.error(f"❌ Error: {e}")  # Emoji in error
```

## Exception Messages

- Use `DriverError` for service-related failures
- Messages should be user-friendly but technical
- Include relevant context (service name, operation)

```python
raise DriverError("TTS service unavailable")
raise DriverError(f"LLM chat failed: {e}")
```
