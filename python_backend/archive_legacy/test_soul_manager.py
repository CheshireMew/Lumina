"""
测试新的 SoulManager 架构
"""
from soul_manager import SoulManager

def test_soul_manager():
    print("[Test] 测试 SoulManager 重构版本...")
    
    # 1. 创建实例
    soul = SoulManager("hiyori")
    print(f"\n[Test] ✅ 成功加载角色: {soul.character_id}")
    
    # 2. 检查数据加载
    print(f"\n[Test] Config: {soul.config.get('display_name')}")
    print(f"[Test] Soul - Traits: {soul.soul.get('personality', {}).get('traits', [])[:3]}")
    print(f"[Test] State - Level: {soul.state.get('galgame', {}).get('relationship', {}).get('level')}")
    
    # 3. 检查兼容性：profile 是否正确合并
    print(f"\n[Test] Merged Profile Keys: {list(soul.profile.keys())}")
    print(f"[Test] Profile Mood: {soul.profile.get('state', {}).get('current_mood')}")
    
    # 4. 测试保存
    print(f"\n[Test] 测试保存功能...")
    soul.profile['personality']['traits'].append("test_trait")
    soul.save_profile()
    print(f"[Test] ✅ save_profile() 执行成功")
    
    # 5. 重新加载验证
    soul2 = SoulManager("hiyori")
    if "test_trait" in soul2.soul.get('personality', {}).get('traits', []):
        print(f"[Test] ✅ 数据持久化成功")
    else:
        print(f"[Test] ❌ 数据持久化失败")
    
    # 清理测试数据
    soul2.soul['personality']['traits'].remove("test_trait")
    soul2.save_soul()
    
    print(f"\n[Test] ✨ 所有测试完成")

if __name__ == "__main__":
    test_soul_manager()
