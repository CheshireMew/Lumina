import logging
import asyncio
from typing import List, AsyncGenerator
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
        
        # ... (Model Mapping - Simplified for brevity in this patch, assuming same logic) ...
        # [Fix] Use Root Endpoint. 
        target_model = "openai" 
        if "mistral" in model.lower() or "mixtral" in model.lower(): target_model = "mistral"
        if "llama" in model.lower(): target_model = "llama"
        if "claude" in model.lower(): target_model = "openai" # Fallback
        if "gemini" in model.lower(): target_model = "gemini"
        if "deepseek" in model.lower(): target_model = "deepseek"
        if "qwen" in model.lower(): target_model = "qwen"
        if "unity" in model.lower(): target_model = "unity"
        if "midijourney" in model.lower(): target_model = "midijourney"
        if "rtist" in model.lower(): target_model = "rtist"
        if "searchgpt" in model.lower(): target_model = "searchgpt"
        if "evil" in model.lower(): target_model = "evil"
        
        url = "https://text.pollinations.ai/" 
        headers = {"Content-Type": "application/json"}
        
        payload = {
            "messages": messages,
            "seed": 42,
            "model": target_model,
            "jsonMode": False
        }

        if stream:
            return self._stream_generator(url, payload, model)
        else:
            # Return Coroutine that results in String
            return await self._fetch_non_stream(url, payload, headers)

    async def _fetch_non_stream(self, url, payload, headers):
        # [Optimization] Use shared HTTP client pool
        from services.http_client import get_http_client
        try:
            client = await get_http_client()
            resp = await client.post(url, json=payload, headers=headers, timeout=120.0)
            if resp.status_code != 200:
                raise Exception(f"Pollinations Error {resp.status_code}: {resp.text}")
            
            try:
                data = resp.json()
                if isinstance(data, str): return data
                if 'choices' in data: return data['choices'][0]['message']['content']
                return str(data)
            except:
                return resp.text
        except Exception as e:
            logger.error(f"Pollinations Req Failed: {e}")
            raise

    async def _stream_generator(self, url: str, payload: dict, model: str) -> AsyncGenerator[str, None]:
        """Pollinations is non-streaming native, so we simulate stream"""
        # [Optimization] Use shared HTTP client pool
        from services.http_client import get_http_client
        try:
            client = await get_http_client()
            # 1. Fetch Full Content (with Retries)
            max_retries = 3
            retry_count = 0
            resp = None
            headers = {"Content-Type": "application/json"}
            
            while retry_count < max_retries:
                try:
                    resp = await client.post(url, json=payload, headers=headers, timeout=30.0 + (retry_count * 10))
                    
                    if resp.status_code == 429:
                        logger.warning(f"Pollinations 429 Queue Full. Retrying {retry_count+1}/{max_retries}...")
                        await asyncio.sleep(2 + (retry_count * 2))  # Backoff: 2s, 4s, 6s...
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
            data = None

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
            if data and isinstance(data, dict):
                if "choices" in data and len(data["choices"]) > 0:
                    msg = data["choices"][0].get("message", {})
                    content = msg.get("content", "")
                    # reasoning = msg.get("reasoning_content", "") # [Debug] Disabled
                elif "error" in data:
                    logger.error(f"Pollinations API Error: {data['error']}")
                    yield f"Error: {data['error']}"
                    return
                else:
                    if "content" in data:
                        content = data["content"]
                    elif not content: 
                         content = resp.text
                    # reasoning remains "" 

            # Fallback: If content is still empty, dump the data so we see what happened
            if not content: 
                 content = str(data) if data else resp.text

            # [Fix] Removed early return to allow deduplication logic to run
            
            # ========== Robust Deduplication ==========
            # Pollinations API sometimes returns content doubled (e.g., "ABCABC")
            # or with line-based prefixes duplicated (e.g., "[happy]\nText\n[happy]\nText").
            
            original_len = len(content)
            
            # Strategy 1: Half-String Comparison
            # If the content is "TEXTTEXT", splitting in half and comparing should reveal a match.
            if original_len > 20:
                half = original_len // 2
                first_half = content[:half]
                second_half = content[half:half + len(first_half)]  # Handle odd length
                
                if first_half == second_half:
                    logger.warning(f"🔁 Detected doubled content (half-match). Deduplicating.")
                    content = first_half
            
            # Strategy 2: Line-Based Prefix Detection
            # If the first few lines repeat later, take only the first occurrence.
            if len(content) > 50:
                lines = content.split('\n')
                if len(lines) > 2:
                    first_line = lines[0].strip()
                    if first_line:
                        # Count occurrences of the first line
                        occurrences = [i for i, l in enumerate(lines) if l.strip() == first_line]
                        if len(occurrences) > 1 and occurrences[1] < len(lines) - 1:
                            logger.warning(f"🔁 Detected line prefix duplication at line {occurrences[1]}. Truncating.")
                            content = '\n'.join(lines[:occurrences[1]])
            
            # Strategy 3: Original "Period Detection" (Fallback for non-half patterns like "ABCABCABC")
            if len(content) > 10:
                for period in range(1, len(content) // 2 + 1):
                    if len(content) % period == 0:
                        unit = content[:period]
                        if unit * (len(content) // period) == content:
                            logger.warning(f"🔁 Detected repeating unit (period: {period}). Deduplicating.")
                            content = unit
                            break
            # ==========================================
            
            logger.info(f"Pollinations Final Content ({len(content)} chars, Original: {original_len})")
            
            chunk_size = 10 
            for i in range(0, len(content), chunk_size):
                chunk = content[i:i+chunk_size]
                yield chunk
                await asyncio.sleep(0.05)

        except Exception as e:
            yield f"Stream Failed: {e}"

    async def list_models(self) -> List[str]:
        return [
            "openai", # GPT-4o-mini
            "mistral", # Mistral Small
            "claude-3-haiku", # [Mapped to OpenAI Fallback]
            "gemini", # Gemini Flash
            # "searchgpt", # [404]
            # "deepseek", # [404] 
            # "qwen-coder", # [404]
            # "llama-3-70b", # [404]
            "midijourney", # Music/Lyrics
            # "evil", # [404]
            # "unity", # [Unverified]
            # "rtist", # [Unverified]
        ]
