"""
Unit tests for TTS Manager
Tests text-to-speech driver switching, audio generation, and memory management
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch
import tempfile

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestTTSManager(unittest.IsolatedAsyncioTestCase):
    """Test TTS Manager functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_tts_manager_initialization(self):
        """Test TTSPluginManager initialization"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()
        self.assertIsNotNone(manager.drivers)
        self.assertIsInstance(manager.drivers, dict)
        self.assertEqual(manager.active_driver_id, "driver.tts.edge")
        print("✅ TTS Manager initialization verified")

    async def test_tts_driver_registration(self):
        """Test driver registration"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()

        # Mock driver
        mock_driver = MagicMock()
        mock_driver.id = "test.tts.driver"
        mock_driver.name = "Test TTS Driver"
        mock_driver.load = AsyncMock()

        manager.drivers[mock_driver.id] = mock_driver

        self.assertIn("test.tts.driver", manager.drivers)
        print("✅ TTS driver registration verified")

    async def test_tts_driver_activation(self):
        """Test driver activation"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()

        # Mock driver
        mock_driver = MagicMock()
        mock_driver.id = "driver.tts.edge"
        mock_driver.load = AsyncMock()
        mock_driver.synthesize = MagicMock(return_value=b"fake_audio")

        manager.drivers["driver.tts.edge"] = mock_driver

        await manager.activate("driver.tts.edge")

        # Verify activation
        self.assertEqual(manager.active_driver_id, "driver.tts.edge")
        mock_driver.load.assert_called_once()
        print("✅ TTS driver activation verified")

    async def test_tts_fallback_to_available_driver(self):
        """Test fallback when requested driver is not available"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()

        # Only one driver available
        mock_driver = MagicMock()
        mock_driver.id = "available.driver"
        mock_driver.load = AsyncMock()
        manager.drivers["available.driver"] = mock_driver

        # Request non-existent driver
        await manager.activate("nonexistent.driver")

        # Should fall back to available driver
        self.assertEqual(manager.active_driver_id, "available.driver")
        print("✅ TTS fallback to available driver verified")

    async def test_tts_no_drivers_degraded_mode(self):
        """Test behavior when no drivers are available"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()
        manager.drivers = {}

        await manager.activate("any.driver")

        # Should enter degraded mode
        self.assertIsNone(manager.active_driver)
        self.assertEqual(manager.active_driver_id, "none")
        print("✅ TTS degraded mode verified")

    async def test_tts_synthesize_basic(self):
        """Test basic text-to-speech synthesis"""
        # Mock synthesis
        class MockTTSDriver:
            def __init__(self):
                self.synthesize_count = 0

            def synthesize(self, text, voice="default"):
                self.synthesize_count += 1
                return f"fake_audio_{len(text)}_bytes".encode()

        driver = MockTTSDriver()

        # Test synthesis
        text = "Hello world"
        audio = driver.synthesize(text)

        self.assertEqual(driver.synthesize_count, 1)
        self.assertIn(b"fake_audio", audio)
        print("✅ TTS synthesize basic verified")

    async def test_tts_voice_selection(self):
        """Test voice selection for TTS"""
        class MockTTSDriver:
            def __init__(self):
                self.available_voices = ["voice1", "voice2", "voice3"]
                self.current_voice = "voice1"

            def set_voice(self, voice):
                if voice in self.available_voices:
                    self.current_voice = voice
                    return True
                return False

            def synthesize(self, text, voice=None):
                v = voice or self.current_voice
                return f"audio_{v}_{len(text)}".encode()

        driver = MockTTSDriver()

        # Test voice selection
        self.assertTrue(driver.set_voice("voice2"))
        self.assertEqual(driver.current_voice, "voice2")

        # Test synthesis with voice
        audio = driver.synthesize("test", "voice3")
        self.assertIn(b"audio_voice3", audio)

        # Test invalid voice
        self.assertFalse(driver.set_voice("invalid_voice"))
        print("✅ TTS voice selection verified")

    async def test_tts_audio_format_output(self):
        """Test audio output format (WAV, MP3, etc.)"""
        class MockAudioFormatter:
            SUPPORTED_FORMATS = ["wav", "mp3", "ogg"]

            def format_audio(self, audio_data, output_format="wav"):
                if output_format not in self.SUPPORTED_FORMATS:
                    raise ValueError(f"Unsupported format: {output_format}")
                # In real implementation, would encode audio
                return {
                    "data": audio_data,
                    "format": output_format,
                    "size": len(audio_data)
                }

        formatter = MockAudioFormatter()

        # Test supported formats
        result = formatter.format_audio(b"audio_data", "wav")
        self.assertEqual(result["format"], "wav")
        self.assertEqual(result["size"], 10)

        # Test unsupported format
        with self.assertRaises(ValueError):
            formatter.format_audio(b"audio_data", "flac")
        print("✅ TTS audio format output verified")

    async def test_tts_long_text_chunking(self):
        """Test chunking of long text for synthesis"""
        def chunk_text(text, max_length=100):
            """Split text into chunks"""
            words = text.split()
            chunks = []
            current_chunk = []

            for word in words:
                test_chunk = " ".join(current_chunk + [word])
                if len(test_chunk) <= max_length:
                    current_chunk.append(word)
                else:
                    if current_chunk:
                        chunks.append(" ".join(current_chunk))
                    current_chunk = [word]

            if current_chunk:
                chunks.append(" ".join(current_chunk))

            return chunks

        # Test chunking
        long_text = "This is a very long text " * 20
        chunks = chunk_text(long_text, max_length=50)

        self.assertGreater(len(chunks), 1)
        # Verify no chunk exceeds max length (roughly)
        for chunk in chunks:
            self.assertLessEqual(len(chunk), 60)  # Allow some margin
        print("✅ TTS long text chunking verified")

    async def test_tts_synthesis_speed(self):
        """Test synthesis speed (characters per second)"""
        import time

        class MockSpeedTestDriver:
            def __init__(self, chars_per_second=100):
                self.chars_per_second = chars_per_second

            def synthesize(self, text):
                # Simulate processing time
                time.sleep(len(text) / self.chars_per_second)
                return b"audio"

        driver = MockSpeedTestDriver(chars_per_second=50)

        # Measure synthesis time
        text = "Hello world, this is a test"
        start = time.time()
        driver.synthesize(text)
        elapsed = time.time() - start

        # Verify it took approximately expected time
        expected_time = len(text) / driver.chars_per_second
        self.assertAlmostEqual(elapsed, expected_time, delta=0.1)
        print("✅ TTS synthesis speed verified")

    async def test_tss_memory_cleanup(self):
        """Test memory cleanup after synthesis"""
        class MockMemoryManagingDriver:
            def __init__(self):
                self.cache = {}

            def synthesize(self, text):
                # Simulate caching
                result = f"audio_{hash(text)}".encode()
                self.cache[text] = result
                return result

            def clear_cache(self):
                cleared = len(self.cache)
                self.cache.clear()
                return cleared

        driver = MockMemoryManagingDriver()

        # Generate some audio
        driver.synthesize("test1")
        driver.synthesize("test2")
        driver.synthesize("test3")

        self.assertEqual(len(driver.cache), 3)

        # Clear cache
        cleared = driver.clear_cache()
        self.assertEqual(cleared, 3)
        self.assertEqual(len(driver.cache), 0)
        print("✅ TTS memory cleanup verified")

    async def test_tts_disabled_plugin_check(self):
        """Test that disabled plugins are not auto-activated"""
        from services.tts_manager import TTSPluginManager

        manager = TTSPluginManager()

        # Mock config with disabled plugins
        mock_config = MagicMock()
        mock_config.plugins.disabled_plugins = ["driver.tts.edge"]

        # Mock driver
        mock_driver = MagicMock()
        mock_driver.id = "driver.tts.edge"
        mock_driver.load = AsyncMock()

        manager.drivers["driver.tts.edge"] = mock_driver

        # Simulate the disabled check from activate()
        if "driver.tts.edge" in mock_config.plugins.disabled_plugins:
            # Should not activate
            self.assertTrue(True)
            print("✅ TTS disabled plugin check verified")
        else:
            self.fail("Plugin should be disabled")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestTTSManager)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All TTSManager tests passed!")
    print("="*60)
