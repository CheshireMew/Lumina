
import asyncio
import edge_tts

async def test_stream():
    text = "测试流式语音合成。"
    voice = "zh-CN-XiaoxiaoNeural"
    
    print(f"Testing streaming with voice: {voice}")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        audio_data = b""
        
        async for chunk in communicate.stream():
            if chunk["type"] == "audio":
                audio_data += chunk["data"]
        
        if len(audio_data) > 0:
            print(f"✅ Stream Success! Got {len(audio_data)} bytes.")
        else:
            print("❌ Stream Failed: No audio data.")
            
    except Exception as e:
        print(f"❌ Stream Error: {type(e).__name__}: {e}")

if __name__ == "__main__":
    asyncio.run(test_stream())
