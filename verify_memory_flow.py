
import requests
import json
import time

BASE_URL = "http://127.0.0.1:8001"

def test_memory_flow():
    print("Testing Memory Flow...")
    
    # 1. Add Memory (Simulate a conversation)
    # We need to make sure the server is configured first. 
    # But since /all returned 200, it is configured.
    # We will try to add a strong fact.
    
    messages = [
        {"role": "user", "content": "My name is Dylan and I love coding in Python."},
        {"role": "assistant", "content": "Nice to meet you Dylan! Python is great."}
    ]
    
    # 0. Configure (with Dummy Key for Pipeline Test)
    print("Configuring with dummy key (expecting 401 later)...")
    try:
        cfg_resp = requests.post(f"{BASE_URL}/configure", json={
            "api_key": "sk-dummy-key-for-testing-pipeline",
            "base_url": "https://api.deepseek.com/v1",
            "model": "deepseek-chat"
        })
        print(f"Config Response: {cfg_resp.status_code} - {cfg_resp.text}")
    except Exception as e:
        print(f"[FAILED] Config Failed: {e}")
        return

    print(f"Adding memory: {messages[0]['content']}")
    try:
        response = requests.post(f"{BASE_URL}/add", json={"messages": messages, "user_id": "test_user"})
        print(f"Add Response: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[FAILED] Add Failed: {e}")
        return

    # Wait for extraction (Mem0 might be async or LLM takes time)
    print("Waiting 10 seconds for extraction...")
    time.sleep(10)

    # 2. Get All Memories
    print("Fetching all memories...")
    try:
        response = requests.get(f"{BASE_URL}/all?user_id=test_user")
        if response.status_code == 200:
            data = response.json()
            print(f"Get All Result: {json.dumps(data, indent=2, ensure_ascii=False)}")
            
            # Check results
            # Expected structure: {"results": {"results": [...]}} or {"results": [...]}
            # Based on user report: {"results": {"results": []}}
            
            # Check ID: 1
            if isinstance(data, list):
                results = data
            else:
                results = data.get("results", [])
                if isinstance(results, dict) and "results" in results:
                     results = results["results"]
            
            if len(results) > 0:
                print("[SUCCESS] Success! Memory stored and retrieved.")
            else:
                print("[FAILED] Failed! Memory list is empty.")
        else:
            print(f"[FAILED] Get All Failed: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"[FAILED] Get All Error: {e}")

if __name__ == "__main__":
    test_memory_flow()
