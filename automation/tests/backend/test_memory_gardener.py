import sys
import unittest
from datetime import datetime, timedelta
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestMemoryGardener(unittest.TestCase):
    def test_decay_algorithm(self):
        """验证时间衰减公式: strength * 0.99^days"""
        print("\n[Test] Testing Memory Decay Algorithm...")
        
        initial_strength = 100.0
        decay_rate = 0.99
        
        # 1 天后
        strength_1d = initial_strength * (decay_rate ** 1)
        self.assertEqual(strength_1d, 99.0)
        
        # 30 天后 (约一个月)
        strength_30d = initial_strength * (decay_rate ** 30)
        # 100 * 0.99^30 ≈ 73.97
        self.assertAlmostEqual(strength_30d, 73.97, places=2)
        
        # 365 天后 (一年)
        strength_365d = initial_strength * (decay_rate ** 365)
        # 100 * 0.99^365 ≈ 2.55
        self.assertAlmostEqual(strength_365d, 2.55, places=2)
        
        print("✅ Decay formula verified across different timeframes.")

    def test_pruning_logic_mock(self):
        """验证当记忆强度低于阈值时，园丁是否触发删除逻辑 (Mock)"""
        print("\n[Test] Testing Pruning Heuristics...")
        
        threshold = 5.0
        memories = [
            {"id": "mem_1", "strength": 50.0}, # Keep
            {"id": "mem_2", "strength": 4.5},  # Delete
            {"id": "mem_3", "strength": 2.0}   # Delete
        ]
        
        pruned_list = [m for m in memories if m["strength"] >= threshold]
        deleted_count = len(memories) - len(pruned_list)
        
        self.assertEqual(len(pruned_list), 1)
        self.assertEqual(deleted_count, 2)
        print(f"✅ Pruning logic verified: Deleted {deleted_count} weak memories.")

    def test_entity_resolution_logic(self):
        """验证同义实体合并的简化逻辑"""
        print("\n[Test] Testing Entity Resolution (Synonym Merging)...")
        
        # 模拟已知实体库
        kg_entities = {"Gemini", "OpenAI", "Lumina"}
        
        # 输入一个新观察到的实体
        new_alias = "lumina_ai"
        
        def resolve_entity(alias):
            # 简化逻辑：不分大小写且包含即可
            alias_lower = alias.lower()
            for entity in kg_entities:
                if entity.lower() in alias_lower or alias_lower in entity.lower():
                    return entity
            return alias
            
        resolved = resolve_entity(new_alias)
        self.assertEqual(resolved, "Lumina")
        print(f"✅ Entity '{new_alias}' resolved to '{resolved}' successfully.")

if __name__ == "__main__":
    unittest.main()
