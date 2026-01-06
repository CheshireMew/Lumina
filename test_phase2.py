
import requests
import time
import json

BASE_URL = "http://127.0.0.1:8001"

def test_add_and_search():
    print("1. Configuring Memory...")
    resp = requests.post(f"{BASE_URL}/configure", json={
        "base_url": "https://api.deepseek.com/v1", # Dummy, mocked in backend if needed
        "api_key": "sk-dummy",
        "character_id": "hiyori"
    })
    print(f"Configure Status: {resp.status_code}")
    print(f"Configure Response: {resp.text}")

    print("2. Adding Memory (Metadata Test)...")
    # We use a phrase that triggers "importance" and specific "emotion"
    payload = {
        "user_id": "test_user",
        "character_id": "hiyori",
        "user_name": "Dylan",
        "char_name": "Hiyori",
        "messages": [
            {"role": "user", "content": "I am so excited because I just won the lottery! My lucky number is 777.", "timestamp": "2026-01-01T12:00:00"}
        ]
    }
    resp = requests.post(f"{BASE_URL}/add", json=payload)
    print(f"Add Response: {resp.json()}")
    
    print("Waiting for async processing (5s)...")
    time.sleep(5)
    
    print("3. Hybrid Search Test...")
    search_payload = {
        "user_id": "test_user",
        "character_id": "hiyori",
        "query": "lucky number",
        "limit": 5,
        "empower_factor": 0.5
    }
    resp = requests.post(f"{BASE_URL}/search/hybrid", json=search_payload)
    
    if resp.status_code == 200:
        results = resp.json()
        print(f"\nFound {len(results)} results:")
        for r in results:
            # Check for generic structure or specific fields
            # SQLite FTS results come as dicts, Qdrant payload as dicts
            # Hybrid search consolidates them.
            print(json.dumps(r, indent=2, ensure_ascii=False))
            
            # Verify Metadata
            if "lucky number" in str(r):
                print("✅ Found expected content")
    else:
        print(f"Search Failed: {resp.text}")

if __name__ == "__main__":
    test_add_and_search()
