"""
STT 模块
========

语音识别功能。

Example:
    text = await lumina.stt.listen()
    result = await lumina.stt.transcribe(audio_bytes)
"""

import logging
from typing import Optional, AsyncIterator
from dataclasses import dataclass

from ..errors import DriverError

logger = logging.getLogger("Lumina.SDK.STT")


@dataclass
class TranscriptResult:
    """识别结果"""
    text: str
    confidence: float = 1.0
    is_final: bool = True
    language: str = "zh"


class STTModule:
    """
    语音识别模块
    
    Methods:
        listen(timeout) - 从麦克风识别
        transcribe(audio) - 从音频数据识别
        listen_stream() - 持续监听
    """
    
    def __init__(self, container):
        self._container = container
    
    def _get_stt_manager(self):
        """Get STT manager or raise DriverError if unavailable."""
        manager = getattr(self._container, 'stt', None)
        if not manager:
            raise DriverError("STT service unavailable")
        return manager
    
    async def listen(self, timeout: float = 10.0) -> TranscriptResult:
        """
        从麦克风识别语音
        
        Args:
            timeout: 超时时间（秒）
        
        Returns:
            识别结果
        
        Example:
            result = await lumina.stt.listen(timeout=5)
            print(result.text)
        """
        stt_manager = self._get_stt_manager()
        
        try:
            if hasattr(stt_manager, 'listen'):
                text = await stt_manager.listen(timeout=timeout)
                return TranscriptResult(text=text)
            elif hasattr(stt_manager, 'recognize'):
                text = await stt_manager.recognize(timeout=timeout)
                return TranscriptResult(text=text)
            else:
                raise DriverError("STT service does not support listen method")
                
        except DriverError:
            raise
        except Exception as e:
            logger.error(f"STT recognition failed: {e}")
            raise DriverError(f"STT recognition failed: {e}")
    
    async def transcribe(self, audio_data: bytes, language: str = "zh") -> TranscriptResult:
        """
        从音频数据识别语音
        
        Args:
            audio_data: 音频数据 (bytes, WAV/PCM 格式)
            language: 语言代码
        
        Returns:
            识别结果
        
        Example:
            with open("audio.wav", "rb") as f:
                result = await lumina.stt.transcribe(f.read())
        """
        stt_manager = self._get_stt_manager()
        
        try:
            if hasattr(stt_manager, 'transcribe'):
                text = await stt_manager.transcribe(audio_data, language=language)
                return TranscriptResult(text=text, language=language)
            elif hasattr(stt_manager, 'recognize_bytes'):
                text = await stt_manager.recognize_bytes(audio_data)
                return TranscriptResult(text=text, language=language)
            else:
                raise DriverError("STT service does not support transcribe method")
                
        except DriverError:
            raise
        except Exception as e:
            logger.error(f"STT transcription failed: {e}")
            raise DriverError(f"STT transcription failed: {e}")
    
    async def listen_stream(self) -> AsyncIterator[TranscriptResult]:
        """
        持续监听语音
        
        Yields:
            识别结果（包含中间结果）
        
        Example:
            async for result in lumina.stt.listen_stream():
                print(result.text)
                if result.is_final:
                    break
        """
        stt_manager = self._get_stt_manager()
        
        if hasattr(stt_manager, 'listen_stream'):
            async for text in stt_manager.listen_stream():
                yield TranscriptResult(text=text, is_final=False)
        else:
            # Fallback: single recognition
            result = await self.listen()
            yield result

