
import sys
import os
import unittest
import json
from datetime import datetime

# Add . to sys.path to import modules
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Import SoulManager (assuming it's in the same dir)
try:
    from soul_manager import SoulManager
except ImportError:
    # If running from root, adjust path or fail
    sys.path.append(os.path.join(os.getcwd(), 'python_backend'))
    from soul_manager import SoulManager

class TestPromptSplit(unittest.TestCase):
    def setUp(self):
        # Mocking SoulManager's initialization
        # We manually create the instance and populate profile
        self.soul_manager = SoulManager.__new__(SoulManager)
        self.soul_manager.character_id = "test_char"
        
        # Mock Profile
        self.soul_manager.profile = {
            "identity": {
                "name": "TestAI",
                "description": "A test AI."
            },
            "personality": {
                "traits": ["Friendly", "Honest"],
                "big_five": {
                    "openness": 0.8,
                    "conscientiousness": 0.7,
                    "extraversion": 0.6,
                    "agreeableness": 0.9,
                    "neuroticism": 0.1
                },
                "pad_model": {
                    "pleasure": 0.9,
                    "arousal": 0.5,
                    "dominance": 0.6
                }
            },
            "state": {
                "energy_level": 80,
                "current_mood": "happy",
                "last_interaction": datetime.now().isoformat()
            },
            "relationship": {
                "user_name": "Tester",
                "level": 2,
                "progress": 50,
                "shared_memories_summary": "We met once.",
                "current_stage_label": "Friend"
            }
        }
        
    def test_render_static_prompt(self):
        """Verify Static Prompt contains only Identity/Guidelines"""
        prompt = self.soul_manager.render_static_prompt()
        
        # Must Have
        self.assertIn("你是 TestAI", prompt)
        self.assertIn("A test AI", prompt)
        self.assertIn("行为准则", prompt)
        
        # Must Not Have (Dynamic elements)
        self.assertNotIn("心情:", prompt, "Static prompt should not contain Mood")
        self.assertNotIn("Openness:", prompt, "Static prompt should not contain Big Five")
        self.assertNotIn("Tester", prompt, "Static prompt should not contain User Name")
        
    def test_render_dynamic_instruction(self):
        """Verify Dynamic Instruction contains State/Traits/Values"""
        instruction = self.soul_manager.render_dynamic_instruction()
        
        # Must Have
        self.assertIn("当前时间", instruction)
        self.assertIn("Tester", instruction) # User Name
        self.assertIn("心情:", instruction)
        self.assertIn("Openness:", instruction) # Big Five moved here
        self.assertIn("Friendly", instruction)  # Traits moved here
        
        # Relationship
        self.assertIn("We met once", instruction)
        
    def test_render_system_prompt_legacy(self):
        """Verify legacy method combines both"""
        full_prompt = self.soul_manager.render_system_prompt()
        self.assertIn("你是 TestAI", full_prompt)
        self.assertIn("当前时间", full_prompt)

if __name__ == '__main__':
    unittest.main()
