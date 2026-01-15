
import os
import sys
import asyncio
import numpy as np

# Setup paths
sys.path.append(os.path.join(os.getcwd(), 'python_backend'))
# Import Engine
from app_config import config
from plugins.drivers.stt.sensevoice.engine import SenseVoiceEngine

async def test_stt():
    print("Initializing SenseVoice Engine...")
    engine = SenseVoiceEngine()
    try:
        engine.initialize()
    except Exception as e:
        print(f"Failed to initialize engine: {e}")
        return

    print("Engine initialized. Generating test audio via EdgeTTS...")
    
    # Generate test audio using edge-tts (cli)
    # We need a wav file. edge-tts usually outputs mp3, but let's try.
    # Actually, generating a wav is easier with simple TTS or just creating a dummy signal?
    # Dummy signal won't produce text.
    # Let's try to find if we have any wav file.
    # No.
    
    # Use edge-tts library if installed? 
    # Let's just create a silent buffer to see if it crashes, 
    # and if possible, use simple synthetic speech if we can.
    # Actually, let's just use a simple sine wave which should output nothing or hallucinate,
    # but at least prove it runs.
    
    # 16kHz, 2 seconds of silence/noise
    sr = 16000
    duration = 2
    t = np.linspace(0, duration, int(sr * duration), endpoint=False)
    # Simple sine wave at 440Hz (A4)
    audio = 0.5 * np.sin(2 * np.pi * 440 * t)
    audio = audio.astype(np.float32)
    
    print(f"Transcribing {duration}s of 440Hz sine wave...")
    try:
        segments, info = engine.transcribe(audio)
        print("Transcription successful!")
        print(f"Detected Language: {info.language}")
        for s in segments:
            print(f"Text: {s.text}")
            
    except Exception as e:
        print(f"Transcribe failed: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    asyncio.run(test_stt())
