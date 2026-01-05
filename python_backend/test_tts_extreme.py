"""
极限对比测试 - 使用最夸张的样式和长文本
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8766"

def test_extreme_emotions():
    """测试极限情感对比"""
    print("🎭 极限情感对比测试")
    print("=" * 80)
    print("⚠️  使用长文本和夸张样式，如果还听不出区别，说明 Edge TTS 不适合")
    print("=" * 80)
    
    # 使用更适合情感表达的音色和更长的文本
    test_cases = [
        {
            "name": "😊 超级开心",
            "voice": "zh-CN-XiaoyiNeural",  # 换用更活泼的音色
            "text": "[happy]哇！太好了太好了！我真的太开心了！这是我这辈子最幸福的时刻！耶！",
            "file": "extreme_happy.mp3"
        },
        {
            "name": "😢 极度悲伤",
            "voice": "zh-CN-XiaoyiNeural",
            "text": "[sad]呜呜呜...我真的好难过...为什么会这样...我的心都要碎了...太痛苦了...",
            "file": "extreme_sad.mp3"
        },
        {
            "name": "😠 暴怒",
            "voice": "zh-CN-YunxiNeural",  # 男声可能更适合愤怒
            "text": "[angry]太过分了！我真的受够了！你们怎么能这样对我！我要发火了！",
            "file": "extreme_angry.mp3"
        },
        {
            "name": "😱 被吓到",
            "voice": "zh-CN-XiaoyiNeural",
            "text": "[shocked]啊！什么！天哪！这不可能！太可怕了！我不敢相信！",
            "file": "extreme_terrified.mp3"
        },
        {
            "name": "😍 深情告白",
            "voice": "zh-CN-XiaoxiaoNeural",  # 温柔女声适合深情
            "text": "[love]我真的很喜欢你...你知道吗...每次见到你我都特别开心...我想永远和你在一起...",
            "file": "extreme_love.mp3"
        },
        {
            "name": "🤫 悄悄话",
            "voice": "zh-CN-XiaoxiaoNeural",
            "text": "[whisper]嘘...我偷偷告诉你一个秘密...你不要告诉别人哦...这件事只有你知道...",
            "file": "extreme_whisper.mp3"
        },
        {
            "name": "💬 平常聊天",
            "voice": "zh-CN-XiaoxiaoNeural",
            "text": "你好，我是小小。今天天气不错，我们聊聊天吧。你最近过得怎么样？",
            "file": "extreme_neutral.mp3"
        }
    ]
    
    output_dir = Path("python_backend/extreme_test")
    output_dir.mkdir(exist_ok=True)
    
    results = []
    
    for i, test in enumerate(test_cases, 1):
        print(f"\n[{i}/{len(test_cases)}] {test['name']}")
        print(f"    音色: {test['voice']}")
        print(f"    文本: {test['text'][:50]}...")
        
        try:
            response = requests.post(
                f"{BASE_URL}/tts/synthesize",
                json={
                    "text": test['text'],
                    "voice": test['voice']
                },
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                output_path = output_dir / test['file']
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"    ✅ 已保存: {test['file']}")
                results.append((test['name'], str(output_path), True))
                time.sleep(0.3)
            else:
                print(f"    ❌ 失败: {response.status_code}")
                results.append((test['name'], "", False))
        
        except Exception as e:
            print(f"    ❌ 错误: {e}")
            results.append((test['name'], "", False))
    
    # 输出测试报告
    print("\n" + "=" * 80)
    print("📊 测试报告")
    print("=" * 80)
    
    success_count = sum(1 for _, _, success in results if success)
    print(f"成功: {success_count}/{len(results)}")
    
    if success_count > 0:
        print(f"\n📁 音频文件位置: {output_dir.absolute()}")
        print("\n🎧 建议播放顺序（最大化对比）:")
        print("   1. extreme_neutral.mp3   (基准 - 普通)")
        print("   2. extreme_happy.mp3     (开心)")
        print("   3. extreme_sad.mp3       (悲伤)")
        print("   4. extreme_angry.mp3     (愤怒)")
        print("   5. extreme_terrified.mp3 (恐惧)")
        print("   6. extreme_love.mp3      (深情)")
        print("   7. extreme_whisper.mp3   (耳语)")
        
        print("\n💡 评估标准:")
        print("   - 如果能听出 3 种以上明显区别 → Edge TTS 可用")
        print("   - 如果只能听出 1-2 种区别 → 效果一般")
        print("   - 如果完全听不出区别 → 需要换方案")

def test_voice_comparison():
    """测试不同音色对情感的表现力"""
    print("\n" + "=" * 80)
    print("🎤 音色情感表现力对比")
    print("=" * 80)
    
    voices = [
        ("zh-CN-XiaoxiaoNeural", "小小（温柔女声）"),
        ("zh-CN-XiaoyiNeural", "晓伊（活泼女声）"),
        ("zh-CN-YunxiNeural", "云希（温暖男声）"),
        ("zh-CN-YunjianNeural", "云健（成熟男声）")
    ]
    
    text = "[happy]今天真的太开心了！我们一起庆祝吧！"
    
    output_dir = Path("python_backend/voice_comparison")
    output_dir.mkdir(exist_ok=True)
    
    print(f"测试文本: {text}")
    
    for voice_id, voice_name in voices:
        print(f"\n测试音色: {voice_name} ({voice_id})")
        
        try:
            response = requests.post(
                f"{BASE_URL}/tts/synthesize",
                json={"text": text, "voice": voice_id},
                stream=True,
                timeout=30
            )
            
            if response.status_code == 200:
                filename = f"voice_{voice_id.split('-')[-1]}.mp3"
                output_path = output_dir / filename
                
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                
                print(f"  ✅ 已保存: {filename}")
            else:
                print(f"  ❌ 失败: {response.status_code}")
        
        except Exception as e:
            print(f"  ❌ 错误: {e}")
    
    print(f"\n📁 音频保存在: {output_dir.absolute()}")
    print("🎧 播放对比，选择情感表现力最好的音色")

if __name__ == "__main__":
    print("🔥 Edge TTS 情感极限测试")
    print()
    
    # 检查服务
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code != 200:
            print("❌ TTS 服务未运行")
            exit(1)
    except:
        print("❌ 无法连接到 TTS 服务")
        print("请先运行: python python_backend/tts_server.py")
        exit(1)
    
    print("✅ TTS 服务正常\n")
    
    # 选择测试
    print("选择测试类型:")
    print("  1. 极限情感对比测试（推荐）")
    print("  2. 音色表现力对比")
    print("  3. 全部测试")
    
    choice = input("\n请输入 (1/2/3, 默认1): ").strip() or "1"
    
    if choice == "1":
        test_extreme_emotions()
    elif choice == "2":
        test_voice_comparison()
    elif choice == "3":
        test_extreme_emotions()
        test_voice_comparison()
    
    print("\n" + "=" * 80)
    print("✨ 测试完成！")
    print("\n如果效果仍不理想，我会为你推荐本地化的高质量 TTS 方案")
    print("=" * 80)
