import logging
import json
import httpx
import time
import asyncio
from typing import Any, List, AsyncGenerator
from core.interfaces.driver import BaseLLMDriver

logger = logging.getLogger("PollinationsDriver")

class PollinationsDriver(BaseLLMDriver):
    def __init__(self, id: str = "pollinations", name: str = "Free Tier (Pollinations)", description: str = "Free AI via Pollinations.ai"):
        super().__init__(id, name, description)
        
    async def load(self):
        pass

    async def chat_completion(self, 
                            messages: list, 
                            model: str, 
                            temperature: float = 0.7, 
                            stream: bool = False,
                            **kwargs):
        
        # Map model names
        target_model = "openai" 
        if "mistral" in model.lower() or "mixtral" in model.lower(): target_model = "mistral"
        if "llama" in model.lower(): target_model = "llama"
        if "unity" in model.lower(): target_model = "unity"
        if "midijourney" in model.lower(): target_model = "midijourney"
        if "rtist" in model.lower(): target_model = "rtist"
        if "searchgpt" in model.lower(): target_model = "searchgpt"

        # [Fix] Use Root Endpoint. 
        # Path-based endpoints (e.g. /mistral) are returning 404.
        # Root endpoint works but might return 429 if busy.
        url = "https://text.pollinations.ai/" 
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "messages": messages,
            "seed": 42,
            "model": target_model,
            "jsonMode": kwargs.get("response_format", {}).get("type") == "json_object"
        }

        if stream:
            # Yield from the stream generator properly
            async for chunk in self._stream_generator(url, payload, model):
                yield chunk
        else:
            async with httpx.AsyncClient(headers=headers, timeout=120.0) as client:
                try:
                    resp = await client.post(url, json=payload)
                    if resp.status_code != 200:
                        raise Exception(f"Pollinations Error {resp.status_code}: {resp.text}")
                    
                    # Pollinations returns straight content string usually, or OpenAI JSON if configured?
                    # Current observation: It often returns OpenAI format OR raw string depending on endpoint ver.
                    # Let's standardize: The current implementation handles both.
                    
                    try:
                        data = resp.json()
                        if isinstance(data, str):
                            yield data
                            return
                        # OpenAI format
                        yield data['choices'][0]['message']['content']
                    except:
                        yield resp.text
                        
                except Exception as e:
                    logger.error(f"Pollinations Req Failed: {e}")
                    raise

    async def _stream_generator(self, url: str, payload: dict, model: str) -> AsyncGenerator[str, None]:
        """Pollinations is non-streaming native, so we simulate stream"""
        async with httpx.AsyncClient(headers={"Content-Type": "application/json"}, timeout=120.0) as client:
            try:
                # 1. Fetch Full Content (with Retries)
                max_retries = 3
                retry_count = 0
                resp = None
                
                while retry_count < max_retries:
                    try:
                        resp = await client.post(url, json=payload, timeout=30.0 + (retry_count * 10))
                        
                        if resp.status_code == 429:
                            logger.warning(f"Pollinations 429 Queue Full. Retrying {retry_count+1}/{max_retries}...")
                            await asyncio.sleep(2 + (retry_count * 2)) # Backoff: 2s, 4s, 6s...
                            retry_count += 1
                            continue
                            
                        # If success or other error, break loop
                        break
                    except Exception as e:
                        logger.warning(f"Pollinations Network Error (Retry {retry_count}): {e}")
                        retry_count += 1
                        await asyncio.sleep(2)
                
                # If still failed or no response
                if not resp or resp.status_code != 200:
                    status = resp.status_code if resp else "timeout"
                    logger.error(f"Pollinations Request Failed after retries. Status: {status}")
                    # SILENT FAIL: Do NOT yield error message to user.
                    # yield "（AI 思考中遇到了点拥堵，请稍后再试...）" 
                    return

                # Attempt to parse as JSON (Direct or Mixed Content)
                import json
                import re
                
                content = ""
                try:
                    data = resp.json()
                    # ... [Standard parsing logic] ...
                except ValueError:
                    # JSON parse failed (likely mixed text + JSON or raw text)
                    text = resp.text
                    # Try to find a JSON block at the end (Pollinations metadata)
                    json_match = re.search(r'(\{.*"choices".*\})$', text, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                            logger.info("Recovered JSON from mixed response tail.")
                        except:
                            data = None
                    else:
                        data = None
                        
                    if data is None:
                        # Assume Raw Text
                        content = text
                
                # Process Data if we have it (Direct or Recovered)
                if 'data' in locals() and isinstance(data, dict):
                    if "choices" in data and len(data["choices"]) > 0:
                        content = data["choices"][0].get("message", {}).get("content", "")
                    elif "error" in data:
                        logger.error(f"Pollinations API Error: {data['error']}")
                        yield "（后端返回错误）"
                        return
                    else:
                        if "content" in data:
                            content = data["content"]
                        elif not content: # meaningful text already set if fallback was used
                             content = resp.text

                if not content: 
                     content = ""
                
                # Robust Deduplication (Finds S+S pattern)
                # Logic: If string S is composed of repeating pattern P, then (S+S).find(S, 1) will return len(P).
                # If len(P) < len(S), it means S is repeating.
                if len(content) > 10:
                    doubled = content + content
                    # Search for 'content' in 'doubled' starting from index 1 (to skip index 0 match)
                    # We only care if it finds it BEFORE the appended copy (i.e., < len(content))
                    idx = doubled.find(content, 1)
                    if idx != -1 and idx < len(content):
                        logger.warning(f"Detected repetitive content (Period: {idx}). Deduplicating.")
                        # Check strictly if it's a clean repeat (it usually is if find works)
                        content = content[:idx]
                
                # Cleanup: If content still looks like it has JSON at the end ...
                # Sometimes Pollinations sends "Hello {json}".
                # If we failed to parse JSON, content="Hello {json}".
                # We should strip the JSON part if we can't parse it?
                # Actually, our regex above tried to extract JSON. If we succeeded, content = Clean.
                # If we failed regex, we yield raw.
                
                logger.info(f"Pollinations Final Content ({len(content)} chars)")
                
                chunk_size = 10 
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield chunk
                    await asyncio.sleep(0.05)



            except Exception as e:
                yield f"Stream Failed: {e}"
    
    def _mock_chunk(self, content: str, model: str) -> str:
        # Return OpenAI Chunk Format String
        return "data: " + json.dumps({
            "id": "chatcmpl-pollinations",
            "object": "chat.completion.chunk",
            "created": int(time.time()),
            "model": model,
            "choices": [{
                "index": 0,
                "delta": {"content": content},
                "finish_reason": None
            }]
        }) + "\n\n"

    async def list_models(self) -> List[str]:
        return ["gpt-4o-mini", "claude-3-haiku", "llama-3-70b", "mistral-large"]
