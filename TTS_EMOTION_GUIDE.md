# TTS 情感合成功能文档

## 功能概述

已为 Lumina 的 TTS 系统添加了情感合成功能，支持通过情感标签控制语音的表达方式。

## 使用方式

### 方式 1: 文本内嵌标签（推荐）

在文本开头添加 `[情感标签]`：

```python
# 示例
text = "[happy]哇，今天天气真好呀！"
text = "[sad]我好难过，你能陪陪我吗？"
text = "[angry]你怎么能这样！"
```

### 方式 2: API 参数

通过 `emotion` 参数指定：

```python
payload = {
    "text": "你好，我是小小！",
    "voice": "zh-CN-XiaoxiaoNeural",
    "emotion": "cheerful"  # 指定情感
}
```

## 支持的情感标签

### 中英文标签映射

| 中文标签 | 英文标签 | Edge TTS 样式 | 说明 |
|---------|---------|--------------|------|
| 开心/快乐/高兴/笑 | happy/joy/smile/laugh | cheerful | 开心欢快 |
| 悲伤/难过/哭 | sad/cry/depressed | sad | 悲伤难过 |
| 生气/愤怒 | angry/mad/annoyed | angry | 生气愤怒 |
| 惊讶 | surprised | excited | 惊喜兴奋 |
| 震惊 | shocked | terrified | 害怕恐惧 |
| 害羞/脸红 | shy/blush | gentle | 温柔轻声 |
| 喜欢/爱 | love/like | affectionate | 深情款款 |
| 思考/困惑/疑问 | thinking/confused | calm | 平静思考 |
| 困/累 | sleepy/tired | gentle | 疲惫轻柔 |
| 默认 | neutral/idle | chat | 闲聊模式 |

### Edge TTS 可用样式

- `cheerful` - 开心欢快
- `sad` - 悲伤
- `angry` - 生气
- `terrified` - 害怕
- `excited` - 兴奋
- `gentle` - 温柔
- `affectionate` - 深情
- `calm` - 平静
- `chat` - 闲聊（默认）
- `customerservice` - 客服
- `whispering` - 耳语

## API 端点

### 1. 合成语音（支持情感）

```http
POST /tts/synthesize
Content-Type: application/json

{
  "text": "[happy]你好！",
  "voice": "zh-CN-XiaoxiaoNeural",
  "emotion": "cheerful"  // 可选
}
```

### 2. 获取情感列表

```http
GET /tts/emotions
```

返回：
```json
{
  "engine": "Edge TTS",
  "emotions": { "happy": "cheerful", ... },
  "available_styles": ["cheerful", "sad", ...],
  "usage": "在文本开头添加 [emotion] 标签"
}
```

### 3. 获取音色列表

```http
GET /tts/voices
```

## 技术实现

### 1. 情感标签解析

```python
def parse_emotion_tags(text: str) -> tuple[str, Optional[str]]:
    """从文本中解析 [emotion]标签"""
    match = re.match(r'^\[([^\]]+)\]\s*(.*)', text)
    if match:
        return match.group(2), match.group(1)
    return text, None
```

### 2. SSML 包装

```python
def wrap_with_ssml(text: str, voice: str, style: Optional[str]):
    """生成带情感样式的 SSML"""
    if style:
        return f"""<speak version='1.0' xmlns:mstts='...'>
            <voice name='{voice}'>
                <mstts:express-as style='{style}'>
                    {text}
                </mstts:express-as>
            </voice>
        </speak>"""
```

### 3. 配置文件

- `tts_emotion_styles.json` - 情感标签到 Edge TTS 样式的映射
- `emotion_map.json` - Live2D 动作映射（前端使用）

## 测试

运行测试脚本：

```bash
python python_backend/test_tts_emotion.py
```

测试内容：
1. 获取情感列表
2. 测试不同情感的语音合成
3. 生成示例音频文件（test_*.mp3）

## 前端集成示例

```typescript
// 调用 TTS API
const response = await fetch('http://127.0.0.1:8766/tts/synthesize', {
  method: 'POST',
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify({
    text: aiResponse,  // AI 返回的文本可能包含 [emotion] 标签
    voice: 'zh-CN-XiaoxiaoNeural'
  })
});

const audioBlob = await response.blob();
const audioUrl = URL.createObjectURL(audioBlob);
audioElement.src = audioUrl;
audioElement.play();
```

## 未来扩展：其他 TTS 引擎

### 架构设计

代码已预留接口，未来可添加其他 TTS 引擎：

```python
# 示例：GPT-SoVITS 引擎
@app.post("/tts/synthesize/gptsovits")
async def synthesize_with_gptsovits(request: TTSRequest):
    """使用 GPT-SoVITS 引擎进行情感语音合成"""
    # 1. 解析情感标签
    clean_text, emotion = parse_emotion_tags(request.text)
    
    # 2. 调用 GPT-SoVITS API
    # （需要安装和配置 GPT-SoVITS）
    
    # 3. 返回音频流
    pass
```

### 推荐的替代引擎

1. **GPT-SoVITS** - 开源克隆 TTS，情感丰富
   - 优点：本地部署、情感自然
   - 缺点：需要训练、配置复杂

2. **VITS** - 高质量端到端 TTS
   - 优点：音质好、延迟低
   - 缺点：情感控制有限

3. **Bark** - AI 生成多情感语音
   - 优点：情感丰富、支持笑声/叹气
   - 缺点：稍慢、显存需求高

### 引擎选择建议

| 引擎 | 情感控制 | 本地部署 | 延迟 | 配置难度 |
|------|---------|---------|------|---------|
| Edge TTS | ⭐⭐⭐ | ❌ 云端 | ⭐⭐⭐⭐⭐ | ⭐⭐⭐⭐⭐ |
| GPT-SoVITS | ⭐⭐⭐⭐⭐ | ✅ | ⭐⭐⭐ | ⭐⭐ |
| VITS | ⭐⭐ | ✅ | ⭐⭐⭐⭐ | ⭐⭐⭐ |
| Bark | ⭐⭐⭐⭐ | ✅ | ⭐⭐ | ⭐⭐⭐⭐ |

## 配置文件格式

### tts_emotion_styles.json

```json
{
  "happy": "cheerful",
  "sad": "sad",
  "angry": "angry"
}
```

### emotion_map.json（前端 Live2D 动作）

```json
{
  "happy": {
    "group": "Idle",
    "index": 4
  }
}
```

## 调试日志

服务会输出详细日志：

```
[TTS] Emotion: happy -> Style: cheerful
[TTS] Streaming synthesis: '哇，今天天气真好呀！' (Style: cheerful)
[TTS] Connection established (Chunk 1: 8192 bytes)
[TTS] Stream completed (15 chunks)
```

## 故障排查

### 问题 1: 情感无效果

**原因**: 音色不支持该样式

**解决**: 使用 `zh-CN-XiaoxiaoNeural`（小小）或 `zh-CN-YunxiNeural`（云希）

### 问题 2: SSML 格式错误

**原因**: 文本包含特殊字符

**解决**: 需要转义 XML 特殊字符（`<`, `>`, `&`, `'`, `"`）

### 问题 3: 映射配置未加载

**原因**: `tts_emotion_styles.json` 文件缺失

**解决**: 确保文件在 `python_backend/` 目录下

## 更新日志

- **2026-01-05**: 初始版本，支持 Edge TTS 情感标签
  - 添加 13 种情感标签（中英文）
  - 支持文本内嵌和参数两种方式
  - 预留其他 TTS 引擎接口

## 参考资料

- [Edge TTS GitHub](https://github.com/rany2/edge-tts)
- [Microsoft SSML 文档](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup)
- [Edge TTS 支持的样式](https://learn.microsoft.com/en-us/azure/ai-services/speech-service/speech-synthesis-markup-voice)
