
import logging
import os
import sys
from mem0 import Memory

# Setup file logging to capture everything
log_file = "mem0_diag.log"
if os.path.exists(log_file):
    os.remove(log_file)

file_handler = logging.FileHandler(log_file, encoding='utf-8')
file_handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
file_handler.setFormatter(formatter)

# Configure Root Logger
root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)
root_logger.addHandler(file_handler)

# Also console
console_handler = logging.StreamHandler(sys.stdout)
console_handler.setLevel(logging.INFO)
root_logger.addHandler(console_handler)

def run_diagnosis():
    print(f"🔬 Starting Mem0 Diagnosis. Logs will be written to {log_file}")
    
    # 1. Configuration (Mirroring Server)
    config = {
        "vector_store": {
            "provider": "qdrant",
            "config": {
                "collection_name": "mem0_diag_test", # Isolated collection
                "path": "./memory_db_diag",
            }
        },
        "llm": {
            "provider": "openai",
            "config": {
                "model": "deepseek-chat",
                "api_key": "sk-aa9ca5621817452e800c149d5a570087", # I need the key. I will try to read from App settings manually or ask user. 
                # CHECK: In the user's logs (Step 2584), I saw: "Initializing LLM Service ... KeyLength: 35". 
                # I don't have the key.
                # However, the server runs because it gets the key from the request.
                # I cannot run this script standalone without the key.
                
                # ALTERNATIVE: I will rely on the `memory_server.py` which I already enabled DEBUG logs for.
                # I will ask the user to find the log file? No, server logs to stdout.
                
                # Let's try to mock the key? No, need real extraction.
                # Check previous files... In `SettingsModal` or `electron-store`? 
                # I cannot read electron-store easily from python script without path guessing.
                
                # OK, I will assume the key is passed via Env Var or ask the user to provide it?
                # No, I will try to use a placeholder and warn if it fails.
                # But wait, the USER has the server running.
                # Maybe I can add a `debug_dump` endpoint to the server?
                
                # BETTER IDEA: Add a `/debug/logs` endpoint to `memory_server.py` that dumps the last N log lines?
                # Implementing in-memory usage logging.
            }
        },
        "embedder": {
            "provider": "huggingface",
            "config": {
                "model": "all-MiniLM-L6-v2",
                "embedding_dims": 384,
                "model_kwargs": {"device": "cpu"}
            }
        }
    }
    
    print("⚠️  Script cannot run without API Key. Aborting standalone diagnosis.")
    print("Instead, I will modify the server to write logs to a file.")

if __name__ == "__main__":
    run_diagnosis()
