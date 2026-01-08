
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
    
    def extract(self, user_input: str, ai_response: str, user_name: str = "User") -> List[Dict]:
        """
        Calls DeepSeek API to extract atomic facts from the conversation.
        Returns a list of fact objects: 
        [
            {"text": "fact string", "emotion": "happy", "importance": 5},
            ...
        ]
        """
        
        prompt = f"""
        You are a Memory Extraction AI. Your job is to extract concise, atomic facts about {user_name} from their message.
        
        **RULES:**
        1. Extract ONLY facts directly stated by {user_name}.
        2. DO NOT extract anything from the AI's response.
        3. Ignore casual conversation (greetings, small talk).
        4. Focus on: preferences, personal details, relationships, specific facts.
        5. Use specific names (e.g. "{user_name}" not "User").
        6. **CRITICAL**: Keep original language (Chinese -> Chinese).
        
        **METADATA EXTRACTION**:
        For each fact, estimate:
        - **emotion**: "happy", "sad", "neutral", "angry", "excited", "anxious". (Based on user's tone)
        - **importance**: 1-10 integer. (1=Trivia/Temporary, 5=Preferences/Opinions, 10=Critical/Permanent Facts like Name, Job, Trauma).
        
        **INPUT:**
        User: "{user_input}"
        AI (Context): "{ai_response}"
        
        **OUTPUT FORMAT**:
        JSON List of Objects.
        Example: 
        [
            {{"text": "{user_name} likes apples", "emotion": "neutral", "importance": 3}},
            {{"text": "{user_name} is terrified of spiders", "emotion": "anxious", "importance": 8}}
        ]
        If no facts, return [].
        JSON Only:
        """

        if self.is_dummy:
            print("[FactExtractor] Using dummy mode. Returning mock structured facts.")
            if "Dylan" in user_input:
                return [
                    {"text": "User's name is Dylan", "emotion": "neutral", "importance": 9},
                    {"text": "User loves Python", "emotion": "happy", "importance": 6}
                ]
            return []

        try:
            payload = {
                "model": "deepseek-chat", 
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a helpful assistant that extracts memory facts."},
                    {"role": "user", "name": user_name, "content": prompt}
                ],
                "stream": False,
                "temperature": 0.0,
                "response_format": {'type': 'json_object'}
            }
            
            # Log LLM interaction for debugging
            prompt_preview = prompt[:100].replace('\n', ' ') + '...' if len(prompt) > 100 else prompt.replace('\n', ' ')
            print(f"[FactExtractor] 调用 LLM 提取事实: {prompt_preview}")
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=10
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Log LLM response
            content_preview = content[:100].replace('\n', ' ') + '...' if len(content) > 100 else content.replace('\n', ' ')
            print(f"[FactExtractor] LLM 返回: {content_preview}")
            
            # Clean up potential markdown code blocks
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            facts = json.loads(content)
            if isinstance(facts, list):
                # Validate structure briefly
                valid_facts = []
                for f in facts:
                    if isinstance(f, dict) and "text" in f:
                        # Ensure defaults
                        f.setdefault("emotion", "neutral")
                        f.setdefault("importance", 1)
                        valid_facts.append(f)
                    elif isinstance(f, str):
                        # Backward compatibility fallback
                        valid_facts.append({"text": f, "emotion": "neutral", "importance": 1})
                return valid_facts
            return []
            
        except Exception as e:
            print(f"[FactExtractor] Error extracting facts: {e}")
            return []

    def extract_batch(self, batch_context: str, focus: str = "user", person_name: str = "User") -> List[Dict]:
        """
        Batch extraction: Process multiple conversations in one LLM call.
        
        Args:
            batch_context: Combined text of multiple conversations with timestamps
            focus: "user" (extract user facts) or "conversation" (extract topics discussed)
            person_name: Name to use in extracted facts (user_name or char_name)
        
        Returns:
            List of fact objects with text, emotion, importance, timestamp
        """
        
        if focus == "user":
            prompt = f"""
You are a Memory Extraction AI. Extract atomic facts about {person_name} from the following conversation history.

**RULES:**
1. Extract ONLY facts directly stated by {person_name}
2. Ignore casual greetings and small talk
3. Focus on: preferences, personal details, relationships, specific facts
4. Use person's actual name: "{person_name}"
5. Keep original language (Chinese → Chinese)
6. Include timestamp in output (inherit from input)

**INPUT (Chronological):**
{batch_context}

**OUTPUT FORMAT:**
JSON List of Objects
[
    {{"text": "{person_name} likes cats", "emotion": "happy", "importance": 5, "timestamp": "2026-01-06 14:30:00"}},
    ...
]

**METADATA:**
- emotion: "happy", "sad", "neutral", "angry", "excited", "anxious"
- importance: 1-10 (1=Trivia, 5=Preferences, 10=Critical)
- timestamp: Inherit from conversation timestamp

If no facts, return []
JSON Only:
"""
        else:  # conversation
            prompt = f"""
You are a Memory Extraction AI. Extract facts about topics discussed between {person_name} and the user.

**RULES:**
1. Extract topics, events, shared experiences
2. Avoid duplicate facts (consolidate similar topics)
3. Use specific names
4. Keep original language

**INPUT:**
{batch_context}

**OUTPUT FORMAT:**
JSON List
[
    {{"text": "Discussed favorite seasons", "emotion": "neutral", "importance": 3, "timestamp": "2026-01-06 14:30:00"}},
    ...
]

JSON Only:
"""
        
        if self.is_dummy:
            print(f"[FactExtractor] Batch mode (dummy). Returning mock facts.")
            return []
        
        try:
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "name": "System", "content": "You are a memory extraction assistant. Output only valid JSON."},
                    {"role": "user", "name": person_name, "content": prompt}
                ],
                "stream": False,
                "temperature": 0.0,
                "response_format": {'type': 'json_object'}
            }
            
            # Log LLM interaction
            prompt_preview = prompt[:100].replace('\n', ' ') + '...' if len(prompt) > 100 else prompt.replace('\n', ' ')
            print(f"[FactExtractor] [Batch] 调用 LLM: {prompt_preview}")

            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=self.headers,
                json=payload,
                timeout=90  # Longer timeout for batch
            )
            response.raise_for_status()
            
            result = response.json()
            content = result['choices'][0]['message']['content'].strip()
            
            # Log LLM response
            content_preview = content[:100].replace('\n', ' ') + '...' if len(content) > 100 else content.replace('\n', ' ')
            print(f"[FactExtractor] [Batch] LLM 返回: {content_preview}")

            # Clean markdown
            if content.startswith("```"):
                content = content.replace("```json", "").replace("```", "").strip()
            
            facts = json.loads(content)
            if isinstance(facts, list):
                valid_facts = []
                for f in facts:
                    if isinstance(f, dict) and "text" in f:
                        f.setdefault("emotion", "neutral")
                        f.setdefault("importance", 1)
                        f.setdefault("timestamp", "")
                        valid_facts.append(f)
                return valid_facts
            return []
            
        except Exception as e:
            print(f"[FactExtractor] Batch extraction error: {e}")
            import traceback
            traceback.print_exc()
            return []

if __name__ == "__main__":
    # Test stub
    pass
