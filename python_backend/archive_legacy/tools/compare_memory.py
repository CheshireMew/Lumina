import requests
import json
import sys
from tabulate import tabulate # Optional, strictly formatting

BASE_URL = "http://127.0.0.1:8001"

def compare_search(query: str, character_id: str = "lillian"):
    print(f"\n🔍 Comparing Search Results for: '{query}' ({character_id})")
    print(f"Server: {BASE_URL}")
    print("-" * 60)

    # 1. Get Qdrant Results (Standard API)
    try:
        resp_q = requests.post(
            f"{BASE_URL}/search",
            json={
                "query": query,
                "character_id": character_id,
                "user_id": "debug_user",
                "limit": 3
            }
        )
        if resp_q.status_code == 200:
            res_q = resp_q.json()
        else:
            print(f"❌ Qdrant API Error: {resp_q.text}")
            res_q = []
    except Exception as e:
        print(f"❌ Qdrant Connection Error: {e}")
        res_q = []

    # 2. Get Surreal Results (Debug API)
    try:
        resp_s = requests.post(
            f"{BASE_URL}/debug/surreal/search",
            json={
                "query": query,
                "agent_id": character_id,
                "limit": 3
            }
        )
        if resp_s.status_code == 200:
            data = resp_s.json()
            res_s = data.get("results", [])
        else:
            print(f"❌ Surreal API Error: {resp_s.text}")
            res_s = []
    except Exception as e:
        print(f"❌ Surreal Connection Error: {e}")
        res_s = []

    # 3. Display Comparison
    # Normalize data for display
    # Qdrant: {'score', 'payload': {'text'}, ...}
    # Surreal: {'score', 'text', ...}

    print("\n🟢 Qdrant (Current Production)")
    if not res_q:
        print("   (No results)")
    for i, r in enumerate(res_q):
        score = r.get('score', 0)
        # Handle different response structures
        # Use .get() on 'r' directly too
        text = r.get('text')
        if not text:
             payload = r.get('payload', {})
             if isinstance(payload, dict):
                 text = payload.get('text', 'N/A')
             else:
                 text = str(payload)
        # Truncate
        text_disp = (text[:60] + '...') if len(text) > 60 else text
        print(f"   {i+1}. [{score:.4f}] {text_disp}")

    print("\n🟣 SurrealDB (New Parallel)")
    if not res_s:
        print("   (No results)")
    for i, r in enumerate(res_s):
        score = r.get('score', 0)
        text = r.get('text', 'N/A')
        text_disp = (text[:60] + '...') if len(text) > 60 else text
        print(f"   {i+1}. [{score:.4f}] {text_disp}")
    
    print("\n✅ Comparison Complete")

if __name__ == "__main__":
    query = "cyberpunk"
    if len(sys.argv) > 1:
        query = " ".join(sys.argv[1:])
    
    compare_search(query)
