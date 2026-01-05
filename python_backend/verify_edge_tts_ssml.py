"""
直接验证 Edge TTS SSML 功能
绕过我们的封装，直接调用 edge-tts 测试
"""
import asyncio
import edge_tts
from pathlib import Path

async def test_ssml_directly():
    """直接使用 edge-tts 库测试 SSML"""
    
    output_dir = Path("python_backend/ssml_verification")
    output_dir.mkdir(exist_ok=True)
    
    tests = [
        {
            "name": "普通文本",
            "text": "你好，我是小小。今天天气不错。",
            "file": "direct_normal.mp3"
        },
        {
            "name": "Cheerful SSML",
            "text": """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='cheerful'>
            太好了！我真的很开心！
        </mstts:express-as>
    </voice>
</speak>""",
            "file": "direct_cheerful.mp3"
        },
        {
            "name": "Whispering SSML",
            "text": """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='whispering'>
            嘘，这是秘密，不要告诉别人。
        </mstts:express-as>
    </voice>
</speak>""",
            "file": "direct_whispering.mp3"
        },
        {
            "name": "Sad SSML",
            "text": """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='sad'>
            我好难过，为什么会这样...
        </mstts:express-as>
    </voice>
</speak>""",
            "file": "direct_sad.mp3"
        }
    ]
    
    print("=" * 80)
    print("🔬 直接测试 Edge TTS SSML（绕过我们的服务）")
    print("=" * 80)
    print()
    
    for test in tests:
        print(f"测试: {test['name']}")
        print(f"输出: {test['file']}")
        
        try:
            communicate = edge_tts.Communicate(test['text'], "zh-CN-XiaoxiaoNeural")
            output_file = output_dir / test['file']
            
            await communicate.save(str(output_file))
            print(f"✅ 完成\n")
        
        except Exception as e:
            print(f"❌ 错误: {e}\n")
    
    print("=" * 80)
    print(f"📁 文件保存在: {output_dir.absolute()}")
    print()
    print("🎧 播放对比:")
    print("   1. direct_normal.mp3 (基准)")
    print("   2. direct_whispering.mp3 (耳语 - 应该音量变小)")
    print("   3. direct_cheerful.mp3 (开心)")
    print("   4. direct_sad.mp3 (悲伤)")
    print()
    print("💡 如果这个测试也听不出区别 → 证明是 Edge TTS 本身的局限")
    print("=" * 80)

if __name__ == "__main__":
    asyncio.run(test_ssml_directly())
