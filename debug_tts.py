
import asyncio
import edge_tts
import os

async def test_tts():
    text = "你好，我是 Lumina。"
    voice = "zh-CN-XiaoxiaoNeural"
    output_file = "test_tts.mp3"
    
    print(f"Testing Edge TTS with voice: {voice}")
    
    try:
        communicate = edge_tts.Communicate(text, voice)
        await communicate.save(output_file)
        
        if os.path.exists(output_file) and os.path.getsize(output_file) > 0:
            print(f"✅ Success! Audio saved to {output_file} ({os.path.getsize(output_file)} bytes)")
        else:
            print("❌ Failed: Output file is empty or missing.")
            
    except Exception as e:
        print(f"❌ Error occurred: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_tts())
