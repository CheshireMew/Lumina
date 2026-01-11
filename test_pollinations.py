
import requests
import json
import time

def test_pollinations():
    print("Testing Pollinations.ai Variants...")
    
    endpoints = [
        ("https://text.pollinations.ai/openai", {"messages": [{"role": "user", "content": "hi"}]}),
        ("https://text.pollinations.ai/", {"messages": [{"role": "user", "content": "hi"}], "model": "openai"}),
        ("https://text.pollinations.ai/mistral", {"messages": [{"role": "user", "content": "hi"}]}),
    ]
    
    headers = {"Content-Type": "application/json"}
    
    for url, payload in endpoints:
        try:
            print(f"   Testing {url} ...")
            resp = requests.post(url, json=payload, headers=headers, timeout=10)
            print(f"   Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"   ✅ SUCCESS! Resp: {resp.text[:50]}...")
                return 
            else:
                print(f"   ❌ Failed: {resp.text[:100]}")
        except Exception as e:
            print(f"   ❌ Exception: {e}")

if __name__ == "__main__":
    test_pollinations()
