"""
测试 edge-tts 的正确 SSML 用法
"""
import asyncio
import edge_tts

async def test_methods():
    """测试不同的调用方式"""
    
    # 方法 1: 纯文本
    print("=" * 60)
    print("方法 1: 纯文本（应该正常）")
    print("=" * 60)
    text = "你好，这是测试。"
    communicate = edge_tts.Communicate(text, "zh-CN-XiaoxiaoNeural")
    await communicate.save("test_method1_plain.mp3")
    print("✅ 保存为 test_method1_plain.mp3\n")
    
    # 方法 2: SSML 作为文本（错误 - 会朗读标签）
    print("=" * 60)
    print("方法 2: SSML 作为 text 参数（错误方式）")
    print("=" * 60)
    ssml = """<speak version='1.0' xmlns='http://www.w3.org/2001/10/synthesis' xmlns:mstts='https://www.w3.org/2001/mstts' xml:lang='zh-CN'>
    <voice name='zh-CN-XiaoxiaoNeural'>
        <mstts:express-as style='cheerful'>
            太好了！
        </mstts:express-as>
    </voice>
</speak>"""
    
    communicate2 = edge_tts.Communicate(ssml, "zh-CN-XiaoxiaoNeural")
    await communicate2.save("test_method2_wrong.mp3")
    print("✅ 保存为 test_method2_wrong.mp3")
    print("⚠️  这个会朗读 SSML 标签内容\n")
    
    # 方法 3: 查看 Communicate 的参数
    print("=" * 60)
    print("方法 3: 检查 Communicate 支持的参数")
    print("=" * 60)
    import inspect
    sig = inspect.signature(edge_tts.Communicate.__init__)
    print("Communicate.__init__ 参数:")
    for param_name, param in sig.parameters.items():
        if param_name != 'self':
            print(f"  - {param_name}: {param.annotation if param.annotation != inspect.Parameter.empty else 'Any'}")
            if param.default != inspect.Parameter.empty:
                print(f"    默认值: {param.default}")
    print()
    
    # 方法 4: 尝试查看源码中的 rate/pitch 等参数
    print("=" * 60)
    print("方法 4: 测试 rate 和 pitch 参数")
    print("=" * 60)
    try:
        communicate3 = edge_tts.Communicate(
            "这是测试快速语音",
            "zh-CN-XiaoxiaoNeural",
            rate="+50%",  # 加快语速
            pitch="+10Hz"  # 提高音调
        )
        await communicate3.save("test_method4_rate.mp3")
        print("✅ rate/pitch 参数有效")
        print("保存为 test_method4_rate.mp3\n")
    except TypeError as e:
        print(f"❌ rate/pitch 参数无效: {e}\n")

if __name__ == "__main__":
    asyncio.run(test_methods())
    
    print("=" * 60)
    print("📌 结论")
    print("=" * 60)
    print("edge-tts 可能:")
    print("1. 不直接支持 SSML（只支持纯文本）")
    print("2. 需要使用其他参数（rate, pitch, volume）来调节")
    print("3. 情感样式可能需要特殊调用方式")
    print()
    print("👉 需要查看 edge-tts 官方文档确认")
