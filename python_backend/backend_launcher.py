import sys
import argparse
import multiprocessing
import os

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_config import IS_FROZEN

def start_stt():
    import stt_server
    import uvicorn
    print("[Launcher] Starting STT Service on port 8765...")
    uvicorn.run(stt_server.app, host="127.0.0.1", port=8765, log_level="info")

def start_tts():
    import tts_server
    import uvicorn
    print("[Launcher] Starting TTS Service on port 8766...")
    uvicorn.run(tts_server.app, host="127.0.0.1", port=8766, log_level="info")

def start_memory():
    # Fix for surreal_memory / main imports
    # main.py is the memory/soul server
    import main as memory_app 
    import uvicorn
    print("[Launcher] Starting Memory/Soul Service on port 8000...")
    uvicorn.run(memory_app.app, host="127.0.0.1", port=8000, log_level="info")

if __name__ == "__main__":
    # Crucial for PyInstaller multiprocessing
    multiprocessing.freeze_support() 
    
    parser = argparse.ArgumentParser(description="Lumina Backend Launcher")
    parser.add_argument("service", choices=["stt", "tts", "memory"], help="Service to launch")
    
    # Parse args (sys.argv[1:])
    try:
        args = parser.parse_args()
        service_map = {
            "stt": start_stt,
            "tts": start_tts,
            "memory": start_memory
        }
        
        # Execute
        service_map[args.service]()
        
    except KeyboardInterrupt:
        print("[Launcher] Service stopped by user.")
    except Exception as e:
        print(f"[Launcher] Critical Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
