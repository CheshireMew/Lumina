
import asyncio
import httpx

async def test_model(model_name, use_path=True):
    base = "https://text.pollinations.ai"
    url = f"{base}/{model_name}" if use_path else base
    
    payload = {
        "messages": [{"role": "user", "content": "Hello"}],
        "model": model_name,
        "seed": 42
    }
    
    label = f"[{model_name} | {'PATH' if use_path else 'ROOT'}]"
    print(f"Testing {label}...")
    async with httpx.AsyncClient() as client:
        try:
            resp = await client.post(url, json=payload, timeout=10)
            print(f"{label} Status: {resp.status_code}")
            if resp.status_code == 200:
                print(f"{label} Success! Response sample: {resp.text[:50]}")
            else:
                pass # print(f"{label} Failed: {resp.text[:50]}")
        except Exception as e:
            print(f"{label} Error: {e}")

async def main():
    models = ["openai", "mistral", "gpt-4o-mini", "llama"]
    tasks = []
    
    for m in models:
        tasks.append(test_model(m, use_path=True))
        tasks.append(test_model(m, use_path=False))
    
    await asyncio.gather(*tasks)

if __name__ == "__main__":
    asyncio.run(main())
