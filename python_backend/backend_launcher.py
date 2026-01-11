import sys
import argparse
import multiprocessing
import os

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_config import IS_FROZEN, config

def start_stt():
    import stt_server
    import uvicorn
    port = config.network.stt_port
    print(f"[Launcher] Starting STT Service on port {port}...")
    uvicorn.run(stt_server.app, host=config.network.host, port=port, log_level="info")

def start_tts():
    import tts_server
    import uvicorn
    port = config.network.tts_port
    print(f"[Launcher] Starting TTS Service on port {port}...")
    uvicorn.run(tts_server.app, host=config.network.host, port=port, log_level="info")

def start_memory():
    # Fix for surreal_memory / main imports
    # main.py is the memory/soul server
    import main as memory_app 
    import uvicorn
    port = config.network.memory_port
    print(f"[Launcher] Starting Memory/Soul Service on port {port}...")
    uvicorn.run(memory_app.app, host=config.network.host, port=port, log_level="info")

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
        
        # Log to file for packaged debugging
        try:
            log_path = os.path.join(os.path.expanduser("~"), "lumina_backend_crash.log")
            with open(log_path, "a", encoding="utf-8") as f:
                f.write(f"\n--- Crash Report [{args.service if 'args' in locals() else 'Unknown'}] ---\n")
                f.write(traceback.format_exc())
        except:
            pass

        sys.exit(1)
