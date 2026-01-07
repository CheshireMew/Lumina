
import requests
import json
import sys

BASE_URL = "http://localhost:8001"

def test_hybrid_search(query, character_id="hiyori"):
    print(f"\n🔍 Testing Hybrid Search for: '{query}' (Character: {character_id})")
    print("-" * 60)
    
    url = f"{BASE_URL}/search/hybrid"
    payload = {
        "user_id": "user",
        "character_id": character_id,
        "query": query,
        "limit": 10, # Top 10 + Graph
        "empower_factor": 1.0
    }
    
    try:
        response = requests.post(url, json=payload)
        response.raise_for_status()
        results = response.json()
        
        if not results:
            print("❌ No memories found.")
            return

        print(f"✅ Found {len(results)} memories:\n")
        
        for i, mem in enumerate(results):
            source = mem.get("source", "unknown")
            score = mem.get("hybrid_score", 0.0)
            text = mem.get("text", "")
            
            # Formatting based on source
            icon = "❓"
            if source == "vector": icon = "🧠 [Vector]"
            elif source == "keyword": icon = "📖 [Keyword]"
            elif source == "graph_association": icon = "🕸️ [Graph]"
            
            print(f"{i+1}. {icon} (Score: {score:.4f})")
            print(f"   Content: {text[:100]}..." if len(text) > 100 else f"   Content: {text}")
            print(f"   Date: {mem.get('timestamp', 'N/A')}")
            
            if "payload" in mem:
                 payload = mem["payload"]
                 if isinstance(payload, dict) and "importance" in payload:
                     print(f"   Importance: {payload['importance']}")
            
            print("")
            
    except requests.exceptions.ConnectionError:
        print("❌ Could not connect to Memory Server. Is it running?")
        print("Run: python python_backend/memory_server.py")
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    if len(sys.argv) > 1:
        query = sys.argv[1]
    else:
        query = "Hello Hiyori"
        
    test_hybrid_search(query)
