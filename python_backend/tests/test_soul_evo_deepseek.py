import sys
import os
import json
import time

# Add python_backend to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'python_backend')))

from soul_manager import SoulManager
from dreaming import DreamingService
from unittest.mock import MagicMock, patch

def test_soul_evolution():
    print("=== Testing Soul Evolution (DeepSeek JSON) ===")
    
    # 1. Setup Mock Memory
    mock_memory = MagicMock()
    # Mock get_random_inspiration to return list of dicts
    mock_memory.get_random_inspiration.return_value = [
        {"content": "Mem 1", "emotion": "happy"},
        {"content": "Mem 2", "emotion": "neutral"},
        {"content": "Mem 3", "emotion": "sad"}
    ]
    # Mock config
    mock_memory.config = {
        "base_url": "http://localhost:11434/v1",
        "api_key": "ollama"
    }
    
    # 2. Setup SoulManager with dummy profile
    # Use ABSOLUTE PATH to avoid SoulManager resolving it relative to itself
    dummy_profile_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "dummy_core_profile.json"))
    print(f"Test Profile Path: {dummy_profile_path}")
    
    # Create dummy profile if not exists
    initial_profile = {
        "personality": {
            "big_five": {
                "openness": 0.5, "conscientiousness": 0.5, "extraversion": 0.5, "agreeableness": 0.5, "neuroticism": 0.5
            },
            "pad_model": {"pleasure": 0.5, "arousal": 0.5, "dominance": 0.5},
            "traits": ["Generic"]
        },
        "relationship": {"current_obsession": "None"}
    }
    with open(dummy_profile_path, "w", encoding='utf-8') as f:
        json.dump(initial_profile, f)
        
    soul = SoulManager(dummy_profile_path)
    
    # 3. Create DreamingService
    # We pass our mock memory
    dreamer = DreamingService(memory_client=mock_memory)
    # Inject our special soul instance
    dreamer.soul = soul
    
    # 4. Mock LLM Response (DeepSeek Format)
    mock_response_json = {
        "analysis": "Test Analysis",
        "new_traits": ["Tested", "Verified"],
        "new_big_five": {
            "openness": 0.99, "conscientiousness": 0.11, "extraversion": 0.88, "agreeableness": 0.77, "neuroticism": 0.22
        },
        "new_pad": {
            "pleasure": 0.9, "arousal": 0.1, "dominance": 0.8
        },
        "current_mood": "[happy]"
    }
    
    # Mock requests.post
    with patch('requests.post') as mock_post:
        mock_response = MagicMock()
        mock_response.json.return_value = {
            'choices': [{'message': {'content': json.dumps(mock_response_json)}}]
        }
        mock_response.raise_for_status.return_value = None
        mock_post.return_value = mock_response
        
        # 5. Run it
        print("Running _analyze_soul_evolution...")
        # Must be > 50 chars to trigger analysis
        dreamer._analyze_soul_evolution("User was testing the system. This is a longer sentence to ensure we pass the length check threshold of 50 characters.")
        
        # 6. Verify Results
        # Check if Soul Updated (by reading file or checking object)
        print("Verifying updates...")
        
        # Reload profile from disk to ensure save_profile worked
        with open(dummy_profile_path, 'r', encoding='utf-8') as f:
            updated_profile = json.load(f)
            
        bf = updated_profile["personality"]["big_five"]
        pad = updated_profile["personality"]["pad_model"]
        traits = updated_profile["personality"]["traits"]
        mood = updated_profile.get("state", {}).get("current_mood", "neutral")
        
        print(f"Big Five: {bf}")
        print(f"PAD: {pad}")
        print(f"Traits: {traits}")
        print(f"Current Mood: {mood}")
        
        assert bf["openness"] == 0.99
        assert pad["pleasure"] == 0.9
        assert "Verified" in traits
        assert mood == "[happy]"
        
        print("✅ Test Passed!")

    # Cleanup
    if os.path.exists(dummy_profile_path):
        os.remove(dummy_profile_path)

if __name__ == "__main__":
    test_soul_evolution()
