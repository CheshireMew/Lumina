"""
Audio Filter Chain.

Manages a chain of audio filters that run before STT processing.
Core code provides this infrastructure, built-in providers register filters.

Design:
- Singleton pattern for global access
- Priority-ordered filter chain
- Fail-open on filter errors (availability over security)
- Async-safe for sounddevice callback integration
"""
import logging
import asyncio
from typing import List, Tuple, Optional, TYPE_CHECKING

if TYPE_CHECKING:
    import numpy as np
    from core.interfaces.audio_filter import IAudioFilter

logger = logging.getLogger("AudioFilterChain")


class AudioFilterChain:
    """
    Manages audio filters in priority order.
    
    This is the internal filter chain used to gate audio before STT.
    When no filters are registered, audio passes through directly.
    """
    
    _instance: Optional["AudioFilterChain"] = None
    
    @classmethod
    def instance(cls) -> "AudioFilterChain":
        """Get singleton instance."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance
    
    @classmethod
    def reset(cls):
        """Reset singleton (for testing)."""
        cls._instance = None
    
    def __init__(self):
        self._filters: List["IAudioFilter"] = []
        self._lock = asyncio.Lock()
        
    async def register(self, filter: "IAudioFilter"):
        """
        Register a new audio filter.
        
        Called by built-in providers during enable().
        Filters are automatically sorted by priority.
        
        Args:
            filter: Provider implementing IAudioFilter
        """
        async with self._lock:
            # Check for duplicate
            if any(f.id == filter.id for f in self._filters):
                logger.warning(f"Filter {filter.id} already registered, skipping")
                return
                
            self._filters.append(filter)
            self._filters.sort(key=lambda f: f.priority)
            logger.info(f"✅ Registered audio filter: {filter.id} (priority: {filter.priority})")
    
    async def unregister(self, filter_id: str):
        """
        Unregister a filter.
        
        Called by built-in providers during disable().
        
        Args:
            filter_id: The filter's unique ID
        """
        async with self._lock:
            original_count = len(self._filters)
            self._filters = [f for f in self._filters if f.id != filter_id]
            
            if len(self._filters) < original_count:
                logger.info(f"🗑️ Unregistered audio filter: {filter_id}")
            else:
                logger.debug(f"Filter {filter_id} was not registered")
    
    async def process(
        self, 
        audio_data: "np.ndarray", 
        sample_rate: int = 16000,
        metadata: dict = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Run audio through all registered filters.
        
        Filters are processed in priority order. If any filter
        rejects the audio, processing stops immediately.
        
        Args:
            audio_data: Raw audio samples
            sample_rate: Sample rate (default 16000)
            metadata: Additional context (audio_id, etc.)
            
        Returns:
            (should_continue, rejection_reason):
            - (True, None): All filters passed, proceed to STT
            - (False, "reason"): Rejected by a filter
        """
        if not self._filters:
            # No filters registered = pass through
            return True, None
        
        metadata = metadata or {}
        
        for filter in self._filters:
            try:
                should_continue, reason = await filter.filter(
                    audio_data, sample_rate, metadata
                )
                if not should_continue:
                    logger.debug(f"🚫 Audio rejected by filter '{filter.id}': {reason}")
                    return False, reason
            except Exception as e:
                # Fail-open: continue on filter error
                # This prioritizes availability over strict filtering
                logger.error(f"Filter '{filter.id}' error (fail-open): {e}", exc_info=True)
                
        return True, None
    
    @property
    def active_filters(self) -> List[str]:
        """List of active filter IDs in priority order."""
        return [f.id for f in self._filters]
    
    @property
    def count(self) -> int:
        """Number of registered filters."""
        return len(self._filters)
