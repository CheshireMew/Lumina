"""
测试 Edge TTS 情感合成功能
"""
import requests
import json

BASE_URL = "http://127.0.0.1:8766"

def test_emotion_list():
    """测试获取情感列表"""
    print("=== 测试 1: 获取支持的情感标签 ===")
    response = requests.get(f"{BASE_URL}/tts/emotions")
    if response.status_code == 200:
        data = response.json()
        print(f"引擎: {data['engine']}")
        print(f"支持的情感标签数量: {len(data['emotions'])}")
        print(f"示例: {list(data['emotions'].items())[:5]}")
        print(f"使用说明: {data['usage']}\n")
    else:
        print(f"错误: {response.status_code}\n")

def test_emotion_synthesis(text, emotion=None, output_file=None):
    """测试带情感的语音合成"""
    print(f"=== 测试合成: {text[:30]}... ===")
    
    payload = {
        "text": text,
        "voice": "zh-CN-XiaoxiaoNeural"
    }
    
    if emotion:
        payload["emotion"] = emotion
    
    response = requests.post(
        f"{BASE_URL}/tts/synthesize",
        json=payload,
        stream=True
    )
    
    if response.status_code == 200:
        if output_file:
            with open(output_file, 'wb') as f:
                for chunk in response.iter_content(chunk_size=8192):
                    f.write(chunk)
            print(f"✅ 合成成功，已保存到: {output_file}\n")
        else:
            print(f"✅ 合成成功\n")
    else:
        print(f"❌ 合成失败: {response.status_code} - {response.text}\n")

if __name__ == "__main__":
    # 1. 获取情感列表
    test_emotion_list()
    
    # 2. 测试不同情感
    test_cases = [
        ("[happy]哇，今天天气真好呀！", None, "test_happy.mp3"),
        ("[sad]我好难过，你能陪陪我吗？", None, "test_sad.mp3"),
        ("[angry]你怎么能这样！", None, "test_angry.mp3"),
        ("你好，我是小小！", "cheerful", "test_emotion_param.mp3"),
        ("普通的语音合成，没有情感", None, "test_neutral.mp3"),
    ]
    
    for text, emotion, output_file in test_cases:
        test_emotion_synthesis(text, emotion, output_file)
    
    print("所有测试完成！请播放生成的 MP3 文件验证效果。")
