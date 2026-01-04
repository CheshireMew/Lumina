
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8001"

def test_configure():
    print("[Test] Configuring...")
    # Using dummy key as we rely on environment or existing setup, 
    # but LiteMemory code needs config passed.
    # Note: Replace with actual key or ensure env is picked up if logic allows.
    # The server expects payload.
    payload = {
        "openai_base_url": "https://api.deepseek.com/v1", # Replace with real or existing one
        "api_key": "YOUR_API_KEY", # !!! Need the actual key from previous config !!
        "model": "deepseek-chat",
        "embedder": "sangmini/msmarco-cotmae-MiniLM-L12_en-ko-ja"
    }
    
    # Simple hack: Reuse what's likely in the system or ask user?
    # Actually, previous memory_server.py startup logs might have hints, 
    # but strictly we need the key.
    # Let's hope the user has set it or we use a placeholder that works if env var is set?
    # LiteMemory uses config['api_key'] directly.
    # I should check if there is a config file to read from.
    pass

def test_workflow():
    # 1. Configure
    # We need the API key. Let's try to find it from a file or environment.
    # If we can't find it, we might fail. 
    # Wait, the user has been running it. Maybe I can grep it? No, security risk.
    # I will ask the user to configure via the Frontend mostly, 
    # but for this script to run, I need a key.
    # Let's assume the server is running and might need a hit.
    
    # Let's try to hit /all to see if it's alive (it returns error if not configured)
    try:
        res = requests.get(f"{BASE_URL}/all")
        print(f"Server status: {res.status_code}")
        if res.status_code == 400:
             print("Server needs config.")
    except Exception as e:
        print(f"Server down? {e}")

if __name__ == "__main__":
    test_workflow()
