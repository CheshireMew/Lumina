"""
统一音色情感测试 - 修正版
所有测试使用同一个音色，纯粹对比情感效果
"""
import requests
import json
import time
from pathlib import Path

BASE_URL = "http://127.0.0.1:8766"

# 使用单一音色
VOICE = "zh-CN-XiaoxiaoNeural"

def get_supported_styles():
    """获取当前音色支持的所有样式"""
    print("📋 查询 Edge TTS 支持的情感样式...")
    try:
        response = requests.get(f"{BASE_URL}/tts/emotions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 加载了 {len(data['emotions'])} 个情感映射")
            print(f"可用样式: {', '.join(data['available_styles'])}\n")
            return data
        else:
            print(f"❌ 无法获取情感列表: {response.status_code}\n")
            return None
    except Exception as e:
        print(f"❌ 连接失败: {e}\n")
        return None

def test_single_emotion(text, description, filename):
    """测试单个情感"""
    print(f"🎤 {description}")
    print(f"   文本: {text}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/tts/synthesize",
            json={"text": text, "voice": VOICE},
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            output_dir = Path("python_backend/unified_test")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / filename
            
            with open(output_path, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            print(f"   ✅ 已保存: {filename}\n")
            return str(output_path)
        else:
            print(f"   ❌ 失败: {response.status_code}\n")
            return None
    
    except Exception as e:
        print(f"   ❌ 错误: {e}\n")
        return None

def main():
    print("=" * 80)
    print("🎭 统一音色情感测试（修正版）")
    print("=" * 80)
    print(f"音色: {VOICE} (小小 - 温柔女声)")
    print("所有测试使用同一音色，确保对比的纯粹性")
    print("=" * 80)
    print()
    
    # 1. 检查服务
    try:
        response = requests.get(f"{BASE_URL}/health", timeout=3)
        if response.status_code != 200:
            print("❌ TTS 服务未运行")
            return
    except:
        print("❌ 无法连接到 TTS 服务")
        print("请先运行: python python_backend/tts_server.py")
        return
    
    # 2. 获取支持的样式
    emotion_data = get_supported_styles()
    
    # 3. 测试用例（按对比度排序）
    test_cases = [
        {
            "text": "你好，我是小小。今天天气不错，我们聊聊天吧。",
            "desc": "0️⃣ 基准 - 普通聊天（chat）",
            "file": "01_neutral.mp3"
        },
        {
            "text": "[happy]哇！太好了太好了！我真的太开心了！这是我这辈子最幸福的时刻！",
            "desc": "😊 开心欢快（cheerful）",
            "file": "02_happy.mp3"
        },
        {
            "text": "[sad]呜呜呜...我真的好难过...为什么会这样...我的心都要碎了...",
            "desc": "😢 悲伤难过（sad）",
            "file": "03_sad.mp3"
        },
        {
            "text": "[angry]太过分了！我真的受够了！你们怎么能这样对我！",
            "desc": "😠 生气愤怒（angry）",
            "file": "04_angry.mp3"
        },
        {
            "text": "[shocked]啊！什么！天哪！这不可能！太可怕了！",
            "desc": "😱 恐惧害怕（terrified）",
            "file": "05_terrified.mp3"
        },
        {
            "text": "[love]我真的很喜欢你...每次见到你我都特别开心...",
            "desc": "😍 深情款款（affectionate）",
            "file": "06_affectionate.mp3"
        },
        {
            "text": "[whisper]嘘...我偷偷告诉你一个秘密...你不要告诉别人哦...",
            "desc": "🤫 耳语轻声（whispering）",
            "file": "07_whispering.mp3"
        },
        {
            "text": "[shy]谢谢你...我、我有点不好意思呢...",
            "desc": "😳 害羞尴尬（embarrassed）",
            "file": "08_embarrassed.mp3"
        }
    ]
    
    print("开始生成测试音频...\n")
    
    results = []
    for i, test in enumerate(test_cases, 1):
        print(f"[{i}/{len(test_cases)}]")
        path = test_single_emotion(test["text"], test["desc"], test["file"])
        results.append((test["desc"], path))
        time.sleep(0.3)
    
    # 4. 生成报告
    print("=" * 80)
    print("📊 测试完成")
    print("=" * 80)
    
    success_count = sum(1 for _, path in results if path)
    print(f"成功: {success_count}/{len(results)}")
    
    if success_count > 0:
        output_dir = Path("python_backend/unified_test")
        print(f"\n📁 音频文件: {output_dir.absolute()}")
        
        print("\n🎧 建议播放顺序（按对比度）:")
        for i, (desc, path) in enumerate(results, 1):
            if path:
                filename = Path(path).name
                print(f"   {i}. {filename:20} - {desc}")
        
        print("\n💡 评估方法:")
        print("   1. 先播放 01_neutral.mp3 建立基准")
        print("   2. 对比播放其他文件")
        print("   3. 重点对比: neutral vs happy vs sad vs angry")
        
        print("\n📝 预期效果:")
        print("   - whispering (耳语) 应该音量明显变小")
        print("   - cheerful (开心) 语调应该上扬")
        print("   - sad (悲伤) 语速应该变慢")
        print("   - angry (愤怒) 语气应该强硬")
        
        print("\n⚠️  如果仍听不出明显区别:")
        print("   → Edge TTS 的情感表现力可能不满足你的需求")
        print("   → 建议切换到 GPT-SoVITS 等本地高情感 TTS")

def test_raw_ssml():
    """测试直接发送 SSML（调试用）"""
    print("\n" + "=" * 80)
    print("🔧 SSML 调试测试")
    print("=" * 80)
    
    # 手动构造 SSML
    ssml_tests = [
        {
            "name": "Cheerful 样式",
            "ssml": """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='cheerful'>
            太好了！我真的很开心！
        </mstts:express-as>
    </voice>
</speak>""",
            "file": "debug_cheerful.mp3"
        },
        {
            "name": "Whispering 样式",
            "ssml": """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='whispering'>
            嘘，这是秘密。
        </mstts:express-as>
    </voice>
</speak>""",
            "file": "debug_whispering.mp3"
        }
    ]
    
    output_dir = Path("python_backend/debug_ssml")
    output_dir.mkdir(exist_ok=True)
    
    for test in ssml_tests:
        print(f"\n测试: {test['name']}")
        print(f"SSML:\n{test['ssml']}\n")
        
        # 直接发送 SSML（不经过我们的封装）
        # 注意：需要修改 Edge TTS 调用方式
        print("⚠️  此功能需要直接调用 edge-tts 库")
        print(f"   建议手动验证 SSML 是否正确")

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1 and sys.argv[1] == "debug":
        test_raw_ssml()
    else:
        main()
