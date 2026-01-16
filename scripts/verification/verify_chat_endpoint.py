import requests
import json
import asyncio
import sys

BASE_URL = "http://127.0.0.1:8010"

def test_chat():
    url = f"{BASE_URL}/lumina/chat/completions"
    payload = {
        # "messages": [], # Optional now
        "user_input": "Hello, tell me a joke about Python.", # Phase 20 Mode
        "user_id": "test_user_001",
        "character_id": "lumina_default",
        "user_name": "Tester",
        "char_name": "Lumina",
        # "long_term_memory": "" # Should rely on RAG
    }
    
    print(f"Testing {url} with payload: {payload}")
    
    try:
        with requests.post(url, json=payload, stream=True, timeout=10) as r:
            if r.status_code != 200:
                print(f"Error: {r.status_code} - {r.text}")
                return
            
            print("Response Stream:")
            for line in r.iter_lines():
                if line:
                    decoded = line.decode('utf-8')
                    if decoded.startswith("data: "):
                        data_content = decoded[6:]
                        if data_content == "[DONE]":
                            print("\n[Stream Complete]")
                            break
                        try:
                            json_data = json.loads(data_content)
                            print(json_data.get("content", ""), end="", flush=True)
                        except:
                            print(f"\n[Raw Data]: {data_content}")
    except Exception as e:
        print(f"Connection Error: {e}")
        print("Ensure the backend server is running on port 8010.")

if __name__ == "__main__":
    test_chat()
