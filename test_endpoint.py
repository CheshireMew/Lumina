
import requests

def test_routes():
    base = "http://127.0.0.1:8010"
    paths = [
        "/v1/chat/completions",
        "/free-llm/v1/chat/completions",
        "/llm/v1/chat/completions", # Maybe LLMManager prefixed it?
        "/docs"
    ]
    
    print(f"Testing routes on {base}...")
    
    for p in paths:
        url = base + p
        try:
            # We assume POST for chat endpoints, GET for docs
            if "docs" in p:
                resp = requests.get(url, timeout=2)
            else:
                resp = requests.post(url, json={"messages": [{"role":"user","content":"hi"}]}, timeout=5)
            
            print(f"[{resp.status_code}] {p}")
        except Exception as e:
            print(f"[ERR] {p}: {e}")

if __name__ == "__main__":
    test_routes()
