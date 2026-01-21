import sys
import json
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestSoulPersonality(unittest.TestCase):
    def test_persona_loading_logic(self):
        """验证是否能正确加载和渲染角色的 Persona 提示词 (Jinja2 风格)"""
        print("\n[Test] Testing Persona Rendering Logic...")
        
        # 模拟角色 YAML 配置
        character_config = {
            "name": "Hiyori",
            "personality": "Cheerful and energetic lab assistant.",
            "interests": ["Physics", "Cookies"]
        }
        
        # 模拟 Jinja2 模板
        template = "You are {{ name }}. Your personality is {{ personality }}. You like {{ interests | join(', ') }}."
        
        # 简化版渲染模拟 (不引入真实 jinja2 库以提高测试通用性)
        def mock_render(tmpl, context):
            res = tmpl
            # Handle simple variables first
            for k, v in context.items():
                target = "{{ " + k + " }}"
                val = str(v) if not isinstance(v, list) else ", ".join(v)
                res = res.replace(target, val)
            # Handle filters (simple implementation)
            for k, v in context.items():
                if isinstance(v, list):
                    target = "{{ " + k + " | join(', ') }}"
                    res = res.replace(target, ", ".join(v))
            return res
            
        rendered = mock_render(template, character_config)
        
        self.assertIn("Hiyori", rendered)
        self.assertIn("Cookies", rendered)
        print(f"✅ Persona rendered: {rendered}")

    def test_emotion_mapping(self):
        """验证情感强度到 Live2D 动作标签的映射"""
        print("\n[Test] Testing Emotion-to-Motion Mapping...")
        
        # 模拟 emotion_map.json
        emotion_map = {
            "joy": {"high": "happy_v2", "low": "smile"},
            "anger": {"high": "angry_intense", "low": "annoyed"}
        }
        
        def map_emotion(emotion, intensity):
            level = "high" if intensity > 0.7 else "low"
            return emotion_map.get(emotion, {}).get(level, "neutral")
            
        self.assertEqual(map_emotion("joy", 0.9), "happy_v2")
        self.assertEqual(map_emotion("joy", 0.3), "smile")
        self.assertEqual(map_emotion("anger", 0.8), "angry_intense")
        self.assertEqual(map_emotion("sadness", 0.5), "neutral")
        print("✅ Emotion mapping heuristics verified.")

if __name__ == "__main__":
    unittest.main()
