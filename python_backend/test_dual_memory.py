import requests
import time
import json

BASE_URL = "http://127.0.0.1:8001"

def print_section(title):
    print(f"\n{'='*20} {title} {'='*20}")

def test_conflict_resolution():
    print_section("Testing Conflict Resolution")
    
    # 1. Set initial fact
    print("[1] Adding initial fact: 'My favorite color is Blue'")
    requests.post(f"{BASE_URL}/add", json={
        "user_id": "user",
        "character_id": "hiyori",
        "messages": [
            {"role": "user", "content": "Start fresh. My favorite color is Blue."},
            {"role": "assistant", "content": "Got it, Blue is your favorite color."}
        ]
    })
    time.sleep(2) # Wait for async processing
    
    # 2. Verify
    print("[2] verifying initial fact...")
    res = requests.post(f"{BASE_URL}/search", json={"user_id": "user", "character_id": "hiyori", "query": "favorite color", "limit": 1}).json()
    print(f"Result: {json.dumps(res, indent=2, ensure_ascii=False)}")
    
    # 3. Add conflicting fact
    print("\n[3] Adding conflicting fact: 'Actually, my favorite color is Red now'")
    requests.post(f"{BASE_URL}/add", json={
        "user_id": "user",
        "character_id": "hiyori",
        "messages": [
            {"role": "user", "content": "Actually, my favorite color is Red now."},
            {"role": "assistant", "content": "Oh, changed to Red? Okay."}
        ]
    })
    time.sleep(5) # Wait for LLM analysis and conflict resolution
    
    # 4. Verify Resolution
    print("[4] Verifying resolution (Expected: Red replacing Blue)...")
    res = requests.post(f"{BASE_URL}/search", json={"user_id": "user", "character_id": "hiyori", "query": "favorite color", "limit": 3}).json()
    print(f"Result: {json.dumps(res, indent=2, ensure_ascii=False)}")

def test_merging():
    print_section("Testing Fact Merging")
    
    # 1. Add first item
    print("[1] Adding: 'I like apples'")
    requests.post(f"{BASE_URL}/add", json={
        "user_id": "user",
        "character_id": "hiyori",
        "messages": [
            {"role": "user", "content": "I like apples."},
            {"role": "assistant", "content": "Apples are great."}
        ]
    })
    time.sleep(2)
    
    # 2. Add additive item
    print("\n[2] Adding: 'I also like bananas'")
    requests.post(f"{BASE_URL}/add", json={
        "user_id": "user",
        "character_id": "hiyori",
        "messages": [
            {"role": "user", "content": "I also like bananas."},
            {"role": "assistant", "content": "Bananas too, nice."}
        ]
    })
    time.sleep(5)
    
    # 3. Verify
    print("[3] Verifying Merging (Expected: Combined fact about apples and bananas)...")
    res = requests.post(f"{BASE_URL}/search", json={"user_id": "user", "character_id": "hiyori", "query": "fruits I like", "limit": 3}).json()
    print(f"Result: {json.dumps(res, indent=2, ensure_ascii=False)}")

if __name__ == "__main__":
    # Configure first
    print("Configuring...")
    requests.post(f"{BASE_URL}/configure", json={
        "api_key": "noop", 
        "base_url": "http://localhost:11434/v1", # Assumes Ollama/local LLM is running
        "character_id": "hiyori"
    })
    
    test_conflict_resolution()
    test_merging()
