
import requests
import json

BASE_URL = "http://127.0.0.1:8001"

def verify_search():
    print(f"Testing Memory Search API at {BASE_URL}")
    
    # 1. First, make sure memory is configured (it might be re-initialized by the server start, but good to be safe/check)
    # Actually, the server initializes it lazily or via config. Let's assume it's initialized or we hit /configure if needed.
    # Based on previous context, user was using it, so it might be ready. 
    # But let's try to hit search directly. If 400, we configure.
    
    query = "我的名字是什么?"
    print(f"Query: {query}")
    
    payload = {
        "user_id": "user",
        "character_id": "hiyori",
        "query": query,
        "limit": 5
    }
    
    try:
        response = requests.post(f"{BASE_URL}/search", json=payload)
        
        if response.status_code == 400 and "not configured" in response.text:
            print("Memory not configured. Configuring now...")
            # Configure
            config_payload = {
                "base_url": "https://api.deepseek.com/v1", # Example, likely ignored if using local DB mostly
                "api_key": "sk-dummy", # We are testing retrieval, extraction needs key but search just needs qdrant
                "character_id": "hiyori"
            }
            conf_resp = requests.post(f"{BASE_URL}/configure", json=config_payload)
            print(f"Configure status: {conf_resp.status_code}")
            
            # Retry search
            response = requests.post(f"{BASE_URL}/search", json=payload)

        print(f"Status Code: {response.status_code}")
        if response.status_code == 200:
            results = response.json()
            if isinstance(results, list):
                print(f"Found {len(results)} results:")
                for res in results:
                    print(f" - [{res.get('score', 0):.4f}] {res.get('text')}")
            else:
                 print(f"Unexpected response format: {results}")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    verify_search()
