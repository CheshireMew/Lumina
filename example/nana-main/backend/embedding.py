import httpx
import asyncio
from typing import List, Optional
import time

class EmbeddingService:
    def __init__(self, api_key: str, api_url: str, model: str, dimension: int):
        self.api_key = api_key
        self.api_url = api_url
        self.model = model
        self.dimension = dimension

    def get_embedding(
        self,
        text: str,
        max_retries: int = 3,
        retry_delay: float = 1.0
    ) -> Optional[List[float]]:
        # 如果输入为空，直接返回 None
        if not text or not text.strip():
            return None
            
        retry_count = 0
        
        # 清理输入文本
        clean_text = text.replace('\r\n', '\n').replace('\r', '\n')
        
        while retry_count <= max_retries:
            try:
                with httpx.Client(verify=False, timeout=30.0) as client:
                    headers = {
                        "Content-Type": "application/json",
                        "Authorization": f"Bearer {self.api_key}"
                    }
                    
                    data = {
                        "model": self.model,
                        "input": clean_text
                    }
                    
                    response = client.post(
                        self.api_url,
                        json=data,
                        headers=headers
                    )
                    
                    if response.status_code != 200:
                        raise Exception(f"Embedding API error: {response.status_code}")
                    
                    response_data = response.json()
                    if "data" not in response_data or not response_data["data"]:
                        raise Exception("Invalid API response format")
                        
                    embedding = response_data["data"][0]["embedding"]
                    print("embedding size:", len(embedding), "embedding:", embedding[0:10])
                    return embedding
                    
            except Exception as e:
                if retry_count == max_retries:
                    print(f"Embedding API调用失败, 超过最大重试次数: {str(e)}")
                    return None
                    
                retry_count += 1
                print(f"Embedding API调用失败，{retry_delay}秒后进行第{retry_count}次重试...")
                time.sleep(retry_delay) 