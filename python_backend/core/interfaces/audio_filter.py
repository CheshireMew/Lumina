"""
Audio Filter Interface for Plugin Integration.
Allows plugins to intercept and filter audio before STT processing.

This is a hook mechanism that enables plugins (like Voiceprint) to
gate audio processing without any core code modification.

Usage:
    1. Plugin implements IAudioFilter
    2. Plugin registers with AudioFilterChain on enable()
    3. Plugin unregisters on disable()
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np


class IAudioFilter(ABC):
    """
    Audio filter plugin interface.
    
    Plugins implement this to intercept audio before STT.
    Multiple filters can be chained, processed in priority order.
    """
    
    @property
    @abstractmethod
    def priority(self) -> int:
        """
        Filter priority. Lower = earlier in chain.
        
        Recommended ranges:
        - 1-50: Security filters (voiceprint, authentication)
        - 51-100: Quality filters (noise reduction, normalization)
        - 101-200: Enhancement filters (echo cancellation)
        
        Default: 100
        """
        pass
    
    @property
    @abstractmethod
    def id(self) -> str:
        """Unique filter ID (e.g., 'voiceprint', 'noise_gate')."""
        pass
    
    @abstractmethod
    async def filter(
        self, 
        audio_data: np.ndarray, 
        sample_rate: int,
        metadata: dict
    ) -> Tuple[bool, Optional[str]]:
        """
        Filter audio data.
        
        This method is called for each audio segment after VAD
        detects speech end, before STT processing.
        
        Args:
            audio_data: Raw audio samples (float32, mono)
            sample_rate: Sample rate (usually 16000)
            metadata: Additional context
                - audio_id: Unique ID for this audio segment
                - timestamp: When speech ended
                
        Returns:
            Tuple of (should_continue, rejection_reason):
            - (True, None): Pass, continue to next filter/STT
            - (False, "reason"): Reject, stop processing this audio
            
        Note:
            This runs in an async context. CPU-bound operations
            should use loop.run_in_executor().
        """
        pass
