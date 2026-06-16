"""
Audio Filter Interface.
Allows built-in providers to filter audio before STT processing.

This is an internal extension point for capabilities like voiceprint gating.

Usage:
    1. Provider implements IAudioFilter
    2. Provider registers with AudioFilterChain on enable()
    3. Provider unregisters on disable()
"""
from abc import ABC, abstractmethod
from typing import Tuple, Optional
import numpy as np


class IAudioFilter(ABC):
    """
    Audio filter provider interface.
    
    Providers implement this to inspect audio before STT.
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
