"""
改进的 TTS 情感测试脚本 - 自动播放音频
需要安装: pip install pygame
"""
import requests
import json
import time
import os
from pathlib import Path

BASE_URL = "http://127.0.0.1:8766"

def test_emotion_list():
    """测试获取情感列表"""
    print("=" * 60)
    print("📋 测试 1: 获取支持的情感标签")
    print("=" * 60)
    try:
        response = requests.get(f"{BASE_URL}/tts/emotions", timeout=5)
        if response.status_code == 200:
            data = response.json()
            print(f"✅ 引擎: {data['engine']}")
            print(f"✅ 支持的情感标签数量: {len(data['emotions'])}")
            print("\n情感映射预览:")
            for emotion, style in list(data['emotions'].items())[:10]:
                print(f"  {emotion:15} -> {style}")
            print(f"\n使用说明: {data['usage']}")
            return True
        else:
            print(f"❌ 错误: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 连接失败: {e}")
        print("⚠️  请确保 TTS 服务正在运行: python python_backend/tts_server.py")
        return False

def test_emotion_synthesis(text, emotion=None, output_file=None, play_audio=True):
    """测试带情感的语音合成"""
    display_text = text[:40] + "..." if len(text) > 40 else text
    print(f"\n🎤 合成: {display_text}")
    
    payload = {
        "text": text,
        "voice": "zh-CN-XiaoxiaoNeural"
    }
    
    if emotion:
        payload["emotion"] = emotion
        print(f"   情感参数: {emotion}")
    
    try:
        response = requests.post(
            f"{BASE_URL}/tts/synthesize",
            json=payload,
            stream=True,
            timeout=30
        )
        
        if response.status_code == 200:
            if output_file:
                output_path = Path(output_file)
                with open(output_path, 'wb') as f:
                    for chunk in response.iter_content(chunk_size=8192):
                        f.write(chunk)
                print(f"✅ 已保存: {output_file}")
                
                # 自动播放
                if play_audio:
                    try:
                        import pygame
                        pygame.mixer.init()
                        pygame.mixer.music.load(str(output_path))
                        pygame.mixer.music.play()
                        
                        # 等待播放完成
                        while pygame.mixer.music.get_busy():
                            time.sleep(0.1)
                        
                        pygame.mixer.quit()
                        print("🔊 播放完成")
                    except ImportError:
                        print("⚠️  未安装 pygame，跳过自动播放")
                        print("   手动播放: ", output_path.absolute())
                    except Exception as e:
                        print(f"⚠️  播放失败: {e}")
                
                return True
            else:
                print(f"✅ 合成成功（未保存）")
                return True
        else:
            print(f"❌ 合成失败: {response.status_code}")
            print(f"   错误详情: {response.text}")
            return False
    except requests.exceptions.Timeout:
        print("❌ 请求超时，TTS 服务可能没有响应")
        return False
    except Exception as e:
        print(f"❌ 发生错误: {e}")
        return False

def interactive_test():
    """交互式情感测试"""
    print("\n" + "=" * 60)
    print("🎭 交互式情感测试")
    print("=" * 60)
    
    emotions_to_test = {
        "开心": "[happy]哇，今天天气真好呀！我们一起出去玩吧！",
        "悲伤": "[sad]我好难过，你能陪陪我吗？",
        "生气": "[angry]你怎么能这样对我！我真的很生气！",
        "惊讶": "[surprised]什么？这怎么可能！太不可思议了！",
        "害羞": "[shy]谢谢你...我有点不好意思呢...",
        "深情": "[love]我真的很喜欢和你在一起的时光。",
        "思考": "[thinking]嗯...让我想想这个问题该怎么回答...",
        "默认": "这是普通的语音合成，没有特殊情感。",
    }
    
    output_dir = Path("python_backend/test_outputs")
    output_dir.mkdir(exist_ok=True)
    
    for emotion_name, text in emotions_to_test.items():
        print(f"\n{'─' * 60}")
        print(f"测试情感: {emotion_name}")
        print(f"{'─' * 60}")
        
        output_file = output_dir / f"emotion_{emotion_name}.mp3"
        success = test_emotion_synthesis(text, None, str(output_file), play_audio=True)
        
        if success:
            # 询问用户反馈
            try:
                feedback = input(f"\n💭 '{emotion_name}' 的情感效果如何？(好/一般/差, 或直接回车跳过): ").strip()
                if feedback:
                    print(f"   记录反馈: {feedback}")
            except KeyboardInterrupt:
                print("\n\n⏸️  测试中断")
                return
        
        time.sleep(0.5)  # 短暂停顿
    
    print(f"\n✅ 所有测试音频已保存到: {output_dir.absolute()}")

def quick_test():
    """快速测试（不播放）"""
    print("\n" + "=" * 60)
    print("⚡ 快速批量测试（生成但不播放）")
    print("=" * 60)
    
    test_cases = [
        ("[happy]太好了！", "test_happy_quick.mp3"),
        ("[sad]好难过...", "test_sad_quick.mp3"),
        ("[angry]太气人了！", "test_angry_quick.mp3"),
        ("普通测试", "test_neutral_quick.mp3"),
    ]
    
    success_count = 0
    for text, output_file in test_cases:
        if test_emotion_synthesis(text, None, output_file, play_audio=False):
            success_count += 1
    
    print(f"\n📊 测试结果: {success_count}/{len(test_cases)} 成功")

if __name__ == "__main__":
    print("🎵 Edge TTS 情感合成测试工具")
    print("=" * 60)
    
    # 1. 检查服务状态
    if not test_emotion_list():
        print("\n❌ 无法连接到 TTS 服务，测试终止")
        exit(1)
    
    # 2. 选择测试模式
    print("\n" + "=" * 60)
    print("请选择测试模式:")
    print("  1. 交互式测试（逐个播放，可评价）")
    print("  2. 快速测试（批量生成，不播放）")
    print("  3. 自定义测试")
    print("=" * 60)
    
    try:
        choice = input("请输入选项 (1/2/3，默认1): ").strip() or "1"
        
        if choice == "1":
            interactive_test()
        elif choice == "2":
            quick_test()
        elif choice == "3":
            print("\n自定义测试:")
            custom_text = input("请输入文本（可包含 [emotion] 标签）: ").strip()
            if custom_text:
                output_file = f"test_custom_{int(time.time())}.mp3"
                test_emotion_synthesis(custom_text, None, output_file, play_audio=True)
        else:
            print("无效选项")
    
    except KeyboardInterrupt:
        print("\n\n👋 测试结束")
    except Exception as e:
        print(f"\n❌ 发生错误: {e}")
    
    print("\n" + "=" * 60)
    print("✨ 测试完成！")
    print("=" * 60)
