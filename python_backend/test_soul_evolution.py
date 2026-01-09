"""
测试 Soul Evolution 触发条件
验证三重条件检查逻辑是否正确
"""
import asyncio
import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_trigger_conditions():
    from surreal_memory import SurrealMemory
    from dreaming import Dreaming
    
    print("\n=== Soul Evolution 触发条件测试 ===\n")
    
    # 连接数据库
    mem = SurrealMemory(url="ws://127.0.0.1:8000/rpc", user="root", password="root")
    await mem.connect()
    
    dream = Dreaming(memory_client=mem, character_id="hiyori")
    
    # 显示当前配置
    print(f"📋 当前触发条件配置:")
    print(f"   - min_interval_minutes: {dream.soul_evolution_config['min_interval_minutes']} 分钟")
    print(f"   - min_memories_threshold: {dream.soul_evolution_config['min_memories_threshold']} 条")
    print(f"   - min_text_length: {dream.soul_evolution_config['min_text_length']} 字符")
    
    # ==================== 测试 1: 全部不满足 ====================
    print("\n\n--- 测试 1: 全部条件不满足 ---")
    dream._processed_memories_since_evolution = 0
    dream._accumulated_text_for_evolution = ""
    dream._last_soul_evolution_time = None
    
    print(f"   Memories: {dream._processed_memories_since_evolution}")
    print(f"   Text Length: {len(dream._accumulated_text_for_evolution)}")
    print(f"   Last Evolution: {dream._last_soul_evolution_time}")
    await dream._check_and_trigger_soul_evolution()
    print("   结果: 应该跳过 ✓")
    
    # ==================== 测试 2: 时间不满足 ====================
    print("\n\n--- 测试 2: 时间间隔不满足 ---")
    dream._processed_memories_since_evolution = 25  # 满足
    dream._accumulated_text_for_evolution = "x" * 600  # 满足
    dream._last_soul_evolution_time = datetime.now() - timedelta(minutes=5)  # 仅 5 分钟前
    
    print(f"   Memories: {dream._processed_memories_since_evolution} (>= 20 ✓)")
    print(f"   Text Length: {len(dream._accumulated_text_for_evolution)} (>= 500 ✓)")
    print(f"   Last Evolution: 5 分钟前 (< 30 分钟 ✗)")
    await dream._check_and_trigger_soul_evolution()
    print("   结果: 应该跳过 ✓")
    
    # ==================== 测试 3: 记忆数量不满足 ====================
    print("\n\n--- 测试 3: 记忆数量不满足 ---")
    dream._processed_memories_since_evolution = 10  # 不满足
    dream._accumulated_text_for_evolution = "x" * 600  # 满足
    dream._last_soul_evolution_time = None  # 满足（从未运行过）
    
    print(f"   Memories: {dream._processed_memories_since_evolution} (< 20 ✗)")
    print(f"   Text Length: {len(dream._accumulated_text_for_evolution)} (>= 500 ✓)")
    print(f"   Last Evolution: None (首次 ✓)")
    await dream._check_and_trigger_soul_evolution()
    print("   结果: 应该跳过 ✓")
    
    # ==================== 测试 4: 文本长度不满足 ====================
    print("\n\n--- 测试 4: 文本长度不满足 ---")
    dream._processed_memories_since_evolution = 25  # 满足
    dream._accumulated_text_for_evolution = "x" * 200  # 不满足
    dream._last_soul_evolution_time = None  # 满足
    
    print(f"   Memories: {dream._processed_memories_since_evolution} (>= 20 ✓)")
    print(f"   Text Length: {len(dream._accumulated_text_for_evolution)} (< 500 ✗)")
    print(f"   Last Evolution: None (首次 ✓)")
    await dream._check_and_trigger_soul_evolution()
    print("   结果: 应该跳过 ✓")
    
    # ==================== 测试 5: 全部满足（会触发 LLM 调用！）====================
    print("\n\n--- 测试 5: 全部条件满足 ---")
    test_text = """
    [2026-01-09 15:00] 用户和Hiyori聊了很久关于艺术和创作的话题，包括对未来人工智能与艺术结合的看法。
    [2026-01-09 15:30] Hiyori表达了对绘画的热爱，她说每次拿起画笔时都能感到内心深处的平静。
    [2026-01-09 16:00] 用户分享了一些生活中的烦恼和压力，Hiyori认真倾听并给予了非常温暖且具有同理心的安慰。
    [2026-01-09 16:15] 他们一起讨论了最近流行的一部关于青春和梦想的动漫，彼此交换了心得。
    """ * 3  # 重复确保超过 500 字符
    
    dream._processed_memories_since_evolution = 25  # 满足
    dream._accumulated_text_for_evolution = test_text  # 满足
    dream._last_soul_evolution_time = None  # 满足（从未运行过）
    
    is_text_ok = len(test_text) >= 500
    print(f"   Memories: {dream._processed_memories_since_evolution} (>= 20 ✓)")
    print(f"   Text Length: {len(dream._accumulated_text_for_evolution)} (>= 500 {'✓' if is_text_ok else '✗'})")
    print(f"   Last Evolution: None (首次 ✓)")
    print("   \n   ⚠️ 即将触发 LLM 调用...")
    
    # 询问是否继续
    confirm = input("   是否继续触发? (y/n): ")
    if confirm.lower() == 'y':
        await dream._check_and_trigger_soul_evolution()
        print("   结果: 已触发演化! ✓")
    else:
        print("   结果: 已跳过")
    
    await mem.db.close()
    print("\n✅ 触发条件测试完成！")

if __name__ == "__main__":
    asyncio.run(test_trigger_conditions())
