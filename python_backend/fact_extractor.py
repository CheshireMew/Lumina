
import os
import requests
import json
from typing import List, Dict

class FactExtractor:
    def __init__(self, api_key: str, base_url: str):
        self.api_key = api_key
        self.base_url = base_url
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        self.is_dummy = self.api_key == "sk-dummy-key-for-testing-pipeline"
    
    def extract(self, user_input: str, ai_response: str, user_name: str = "User") -> List[str]:
        """
        Calls DeepSeek API to extract atomic facts from the conversation.
        Returns a list of fact strings (e.g., ["Dylan likes blue", "Dylan lives in New York"]).
        """
        
        prompt = f"""
        You are a Memory Extraction AI. Your job is to extract concise, atomic facts about {user_name} from their message ONLY.
        
        **RULES:**
        1. Extract ONLY facts directly stated by {user_name} in their message
        2. DO NOT extract anything from the AI's response
        3. Ignore casual conversation (greetings, small talk, questions)
        4. Focus on: user preferences, personal details, relationships, specific facts
        5. Each fact should be standalone and atomic
        6. Use the specific name "{user_name}" instead of "User" or "He/She". (e.g., "{user_name} likes X")
        7. **CRITICAL: Output facts in the SAME LANGUAGE as the User's Input.** (e.g. Chinese -> Chinese, English -> English)
        
        **User's Message:**
        "{user_input}"
        
        **AI's Response (for context only, DO NOT extract from this):**
        "{ai_response}"
        
        **Examples:**
        - If {user_name} says "我喜欢橘子", extract: ["{user_name}喜欢橘子"]
        - If {user_name} says "My name is Alice", extract: ["{user_name}'s name is Alice"]
        - If {user_name} only asks a question, return: []
        
        Output a JSON list of fact strings. If no facts found, return [].
        Output (JSON only):
        """

        if self.is_dummy:
            print("[FactExtractor] Using dummy mode. Returning mock facts.")
            # Mock extraction based on input "My name is Dylan..."
            if "Dylan" in user_input:
                return ["User's name is Dylan", "User loves coding in Python"]
            return ["User provided input"]

        try:
            payload = {
                "model": "deepseek-chat", # Or whatever model name is configured
                "messages": [
                    {"role": "system", "content": "You are a helpful assistant that extracts memory facts."},
                    {"role": "user", "content": prompt}
                ],
                "stream": False,
                "temperature": 0.0
            }
            
            # Note: memory_server.py seems to use "model" in config. 
            # We will rely on the caller to pass the right model or default to known working one.
            # Assuming 'deepseek-chat' or similar. 
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Clean up potential markdown code blocks
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            facts = json.loads(content)
            if isinstance(facts, list):
                return sorted(facts) # Sort for consistency
            return []
            
        except Exception as e:
            print(f"[FactExtractor] Error extracting facts: {e}")
            return []

if __name__ == "__main__":
    # Test stub
    pass
