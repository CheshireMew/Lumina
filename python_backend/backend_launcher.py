import sys
print(f"DEBUG_TRACE: Loading backend_launcher.py from {__file__}", flush=True)
import argparse
import multiprocessing
import os

# Ensure local imports work
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app_config import config

def start_stt():
    import generic_worker
    from argparse import Namespace
    
    # Inject Args for Generic Worker
    generic_worker.args = Namespace(
        capability="stt",
        host=config.network.host,
        port=config.network.stt_port
    )
    
    import uvicorn
    port = config.network.stt_port
    print(f"[Launcher] Starting STT Service (Generic Helper) on port {port}...")
    uvicorn.run(generic_worker.app, host=config.network.host, port=port, log_level="info", log_config=None)

def start_tts():
    import generic_worker
    from argparse import Namespace
    
    # Inject Args for Generic Worker
    generic_worker.args = Namespace(
        capability="tts",
        host=config.network.host,
        port=config.network.tts_port
    )

    import uvicorn
    port = config.network.tts_port
    print(f"[Launcher] Starting TTS Service (Generic Helper) on port {port}...")
    uvicorn.run(generic_worker.app, host=config.network.host, port=port, log_level="info", log_config=None)

def start_memory():
    # [Refactor] Memory is now a Generic Worker Capability
    # Previously it ran 'main.py' directly.
    # To support migration, we offer two modes:
    # 1. Legacy Monolith (runs main.py) - Default if no args?
    # 2. Worker Mode (generic_worker --capability memory)
    # The user instruction was to MIGRATE. 
    # But main.py IS the Gateway/Soul server. It NEEDS to run.
    # If we run 'memory' as a worker, main.py still needs to run as Gateway/Soul.
    # So 'start_memory' in launcher usually meant "Start the Main Server".
    # We should probably Rename `start_memory` to `start_main` or `start_core`.
    # AND add `start_memory_worker`.
    # However, existing ecosystem expects `python backend_launcher.py memory` to start the "Main Brain".
    # So we should KEEP `start_memory` pointing to `main.py` for now, BUT `main.py` should be stripped of Helper Logic if Config says so.
    
    # WAIT. User wants "stt_server.py ... abstracted".
    # If we abstract Memory, we have a Memory Worker.
    # `main.py` becomes just Soul/Gateway.
    # So we need a NEW entry in launcher for "Core" (main.py) and change "Memory" to be the Worker?
    # No, that breaks compatibility violently.
    # Let's keep `start_memory` launching `main.py` (Monolith) for now, 
    # and add `start_memory_worker` for the new Isolated Capability?
    # OR, if the user intends to run Distributed, they run:
    # 1. launcher memory_worker
    # 2. launcher core (main.py)
    
    # For now, let's inject `start_memory_node` -> Generic Worker.
    # And keep `start_memory` -> Main.py (renamed to start_core ideally, but keep alias).
    
    import main as memory_app 
    import uvicorn
    port = config.network.memory_port
    print(f"[Launcher] Starting Core System (Soul/Gateway) on port {port}...")
    host = "127.0.0.1" if config.network.bind_localhost_only else config.network.host
    uvicorn.run(memory_app.app, host=host, port=port, log_level="info", log_config=None)

def start_memory_worker():
    import generic_worker
    from argparse import Namespace
    
    generic_worker.args = Namespace(
        capability="memory",
        host=config.network.host,
        port=8006 # Discrete port for Memory Worker
    )
    
    import uvicorn
    # Config need a memory_worker_port?
    port = 8006
    print(f"[Launcher] Starting Memory Worker on port {port}...")
    uvicorn.run(generic_worker.app, host=config.network.host, port=port, log_level="info", log_config=None)



def start_vision():
    import generic_worker
    from argparse import Namespace
    
    # Inject Args for Generic Worker
    # Vision doesn't have a port in config usually, let's pick 8003 or similar, or look it up
    # For now, let's assume 8005 or define in config.
    # But ConfigManager might not have vision_port.
    # Let's just default to 8005 for now.
    generic_worker.args = Namespace(
        capability="vision",
        host=config.network.host,
        port=8005
    )

    import uvicorn
    port = 8005
    print(f"[Launcher] Starting Vision Service (Generic Helper) on port {port}...")
    uvicorn.run(generic_worker.app, host=config.network.host, port=port, log_level="info", log_config=None)

if __name__ == "__main__":
    # Crucial for PyInstaller multiprocessing
    multiprocessing.freeze_support() 
    
    parser = argparse.ArgumentParser(description="Lumina Backend Launcher")
    parser.add_argument("service", choices=["stt", "tts", "memory", "vision", "memory_worker"], help="Service to launch")
    
    # Parse args (sys.argv[1:])
    try:
        args = parser.parse_args()
        service_map = {
            "stt": start_stt,
            "tts": start_tts,
            "memory": start_memory,
            "vision": start_vision,
            "memory_worker": start_memory_worker
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
