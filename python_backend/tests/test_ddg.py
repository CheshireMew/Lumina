
import asyncio
import httpx
import re

async def test_ddg_scrape():
    print("Testing VQD Scrape from Homepage...")
    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    }
    async with httpx.AsyncClient(headers=headers, timeout=30.0) as client:
        try:
            # 1. Hit Homepage
            print("   - Requesting https://duckduckgo.com/ ...")
            resp = await client.get("https://duckduckgo.com/")
            print(f"     Status: {resp.status_code}")
            
            # 2. Extract VQD
            # Look for vqd='4-...' or vqd="4-..."
            text = resp.text
            match = re.search(r'vqd=[\'"]([0-9-]+)[\'"]', text)
            if match:
                token = match.group(1)
                print(f"   ✅ Found VQD in HTML: {token}")
                
                # Try Chat with this token
                chat_headers = headers.copy()
                chat_headers["x-vqd-4"] = token
                chat_headers["Content-Type"] = "application/json"
                chat_headers["Accept"] = "text/event-stream"
                
                payload = {
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "user", "content": "Hello"}]
                }
                
                print("   - Testing Chat with scraped token...")
                async with client.stream("POST", "https://duckduckgo.com/duckchat/v1/chat", json=payload, headers=chat_headers) as r:
                    if r.status_code == 200:
                        print("     ✅ Chat Works!")
                        async for line in r.aiter_lines():
                            if line:
                                print(line[:50])
                                break
                    else:
                        print(f"     ❌ Chat Failed: {r.status_code}")
                        print(await r.aread())

            else:
                print("   ❌ No VQD found in HTML.")

        except Exception as e:
            print(f"❌ Error: {e}")

if __name__ == "__main__":
    asyncio.run(test_ddg_scrape())
