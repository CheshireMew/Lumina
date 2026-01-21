import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))

class TestVisionService(unittest.TestCase):
    @patch("mss.mss")
    def test_screen_capture_packet(self, mock_mss):
        """验证屏幕截图是否能生成正确的 Base64 格式 (Mock)"""
        print("\n[Test] Testing Screen Capture Serialization...")
        
        # 模拟 mss 截图返回
        mock_instance = mock_mss.return_value
        mock_instance.monitors = [None, {"top": 0, "left": 0, "width": 1920, "height": 1080}]
        
        mock_img = MagicMock()
        mock_img.rgb = b"fake_rgb_data"
        mock_img.size = (1920, 1080)
        mock_instance.grab.return_value = mock_img
        
        # 模拟 PNG 转换
        with patch("mss.tools.to_png", return_value=b"fake_png_bytes"):
            from services.vision_service import VisionService
            service = VisionService()
            
            b64_result = service.capture_screen_base64()
            
            self.assertIsNotNone(b64_result)
            self.assertTrue(b64_result.startswith("data:image/png;base64,"))
            print(f"✅ Screen capture serialized to Base64 successfully.")

    def test_vision_driver_fallback(self):
        """验证当默认视觉驱动不可用时，系统是否能自动降级"""
        print("\n[Test] Testing Vision Driver Fallback Flow...")
        
        from services.vision_service import VisionService
        service = VisionService()
        
        # 注入模拟驱动
        mock_driver = MagicMock(id="fallback_driver")
        service.drivers = {"fallback_driver": mock_driver}
        service.active_driver_id = "non_existent_model"
        
        provider = service.get_active_provider()
        self.assertEqual(provider.id, "fallback_driver")
        print(f"✅ Successfully fell back to available driver: {provider.id}")

if __name__ == "__main__":
    unittest.main()
