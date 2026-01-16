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
            "jsonMode": False # kwargs.get("response_format", {}).get("type") == "json_object"
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
                    
                    try:
                        data = resp.json()
                        if isinstance(data, str):
                            yield data
                            return
                        # OpenAI format
                        if 'choices' in data:
                             yield data['choices'][0]['message']['content']
                        else:
                             yield str(data)
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
                    return

                # Attempt to parse as JSON (Direct or Mixed Content)
                import json
                import re
                
                content = ""
                try:
                    data = resp.json()
                except ValueError:
                    text = resp.text
                    json_match = re.search(r'(\{.*"choices".*\})$', text, re.DOTALL)
                    if json_match:
                        try:
                            data = json.loads(json_match.group(1))
                        except:
                            data = None
                    else:
                        data = None
                        
                    if data is None:
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
                        elif not content: 
                             content = resp.text

                if not content: 
                     content = ""
                
                # Robust Deduplication (Finds S+S pattern)
                if len(content) > 10:
                    doubled = content + content
                    idx = doubled.find(content, 1)
                    if idx != -1 and idx < len(content):
                        logger.warning(f"Detected repetitive content (Period: {idx}). Deduplicating.")
                        content = content[:idx]
                
                logger.info(f"Pollinations Final Content ({len(content)} chars)")
                
                chunk_size = 10 
                for i in range(0, len(content), chunk_size):
                    chunk = content[i:i+chunk_size]
                    yield chunk
                    await asyncio.sleep(0.05)

            except Exception as e:
                yield f"Stream Failed: {e}"

    async def list_models(self) -> List[str]:
        return ["gpt-4o-mini", "claude-3-haiku", "llama-3-70b", "mistral-large"]
