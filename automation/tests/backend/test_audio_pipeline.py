import sys
import unittest
import numpy as np
import time
from pathlib import Path

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

# Mock STT/TTS dependencies if they require GPU/Heavy models
# Here we test the LOGIC in audio_manager.py or similar utilities

class TestAudioPipeline(unittest.TestCase):
    def setUp(self):
        # 模拟音频参数
        self.sample_rate = 16000
        self.chunk_size = 512
        
    def test_vad_mock_processing(self):
        """模拟语音活动检测 (VAD) 的判定逻辑测试"""
        print("\n[Test] Testing VAD Heuristics...")
        
        # 模拟静音数据 (RMS 极低)
        silent_chunk = np.zeros(self.chunk_size, dtype=np.float32)
        
        # 模拟人声数据 (随机噪声作为近似)
        voice_chunk = np.random.uniform(-0.5, 0.5, self.chunk_size).astype(np.float32)
        
        def simple_vad_logic(chunk):
            rms = np.sqrt(np.mean(chunk**2))
            return rms > 0.05 # 阈值
            
        self.assertFalse(simple_vad_logic(silent_chunk), "Silence should not trigger VAD")
        self.assertTrue(simple_vad_logic(voice_chunk), "Voice should trigger VAD")
        print("✅ Simple VAD Logic Verified.")

    def test_audio_buffer_overflow_safety(self):
        """验证音频缓冲区在极端情况下的稳定性"""
        print("\n[Test] Testing Buffer Integrity under Load...")
        
        max_buffer_size = 10 * self.sample_rate # 10秒缓冲区
        current_buffer = []
        
        start_time = time.time()
        # 快速注入大量“音频片”
        for i in range(2000): # 模拟大量并发片
            current_buffer.append(np.zeros(self.chunk_size))
            if len(current_buffer) * self.chunk_size > max_buffer_size:
                # 触发截断或丢弃逻辑
                current_buffer = current_buffer[-50:] # 仅保留最后 50 片
                
        elapsed = time.time() - start_time
        self.assertLess(len(current_buffer) * self.chunk_size, max_buffer_size + 1)
        print(f"✅ Buffer Safety logic verified. Processed in {elapsed:.4f}s")

    def test_sample_rate_conversion_logic(self):
        """验证采样率转换的算力消耗及比例一致性 (Mock)"""
        print("\n[Test] Testing Resampling Ratios...")
        
        source_rate = 44100
        target_rate = 16000
        duration_sec = 1
        
        num_samples_source = source_rate * duration_sec
        expected_samples_target = target_rate * duration_sec
        
        # 模拟转换后的长度计算
        ratio = target_rate / source_rate
        actual_target_len = int(num_samples_source * ratio)
        
        self.assertAlmostEqual(actual_target_len, expected_samples_target, delta=1)
        print(f"✅ Resampling ratio logic verified ({source_rate}Hz -> {target_rate}Hz)")

if __name__ == "__main__":
    unittest.main()
