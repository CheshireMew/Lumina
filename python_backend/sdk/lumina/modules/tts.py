"""
TTS Module
==========

Text-to-speech functionality.

Example:
    await lumina.tts.speak("Hello world")
    audio = await lumina.tts.synthesize("Hello", voice="xiaoming")
"""

import logging
from typing import Optional, Dict, Any

from ..errors import DriverError
from ..utils import get_service_or_raise, driver_error_handler

logger = logging.getLogger("Lumina.SDK.TTS")


class TTSModule:
    """
    Text-to-speech module
    
    Methods:
        speak(text, **options) - Synthesize and play audio
        synthesize(text, **options) - Synthesize only, return audio data
    """
    
    def __init__(self, container):
        self._container = container
    
    def _get_tts_manager(self):
        """Get TTS manager or raise DriverError if unavailable."""
        return get_service_or_raise(self._container, 'tts', 'TTS')
    
    @driver_error_handler("TTS", "speak")
    async def speak(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        **kwargs
    ) -> None:
        """
        Synthesize and play speech
        
        Args:
            text: Text to speak
            voice: Voice name (optional, uses user default)
            speed: Speed rate (0.5-2.0)
            emotion: Emotion (happy/sad/angry/neutral)
        
        Raises:
            DriverError: TTS driver error
            TimeoutError: Timeout
        
        Example:
            await lumina.tts.speak("Hello")
            await lumina.tts.speak("Hello", voice="xiaoming", speed=1.2)
        """
        # Synthesize audio
        audio_data = await self.synthesize(
            text, voice=voice, speed=speed, emotion=emotion, **kwargs
        )
        
        # Play via system audio pipeline
        if audio_data:
            await self._play_audio(audio_data)
    
    @driver_error_handler("TTS", "synthesis")
    async def synthesize(
        self,
        text: str,
        *,
        voice: Optional[str] = None,
        speed: float = 1.0,
        emotion: Optional[str] = None,
        **kwargs
    ) -> bytes:
        """
        Synthesize speech, return audio data
        
        Args:
            text: Text to synthesize
            voice: Voice name
            speed: Speed rate
            emotion: Emotion
        
        Returns:
            Audio data (bytes, WAV format)
        
        Example:
            audio = await lumina.tts.synthesize("Hello")
            with open("output.wav", "wb") as f:
                f.write(audio)
        """
        tts_manager = self._get_tts_manager()
        
        # Build options
        options = {
            "speed": speed,
            **kwargs
        }
        if voice:
            options["voice"] = voice
        if emotion:
            options["emotion"] = emotion
        
        # Call underlying service
        result = await tts_manager.synthesize_async(text, **options)
        return result
    
    async def _play_audio(self, audio_data: bytes):
        """Play audio data"""
        tts_manager = getattr(self._container, 'tts', None)
        if tts_manager and hasattr(tts_manager, 'play_audio'):
            await tts_manager.play_audio(audio_data)

