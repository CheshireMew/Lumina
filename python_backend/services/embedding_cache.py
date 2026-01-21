"""
Embedding Cache

LRU cache for vector embeddings to avoid repeated computation.
Embeddings are expensive (~50-100ms per encode), caching identical
queries significantly improves RAG response time.

Usage:
    from services.embedding_cache import get_embedding_cached, get_cache_stats
    
    vector = get_embedding_cached(text, model)
    stats = get_cache_stats()
"""

import logging
import hashlib
import time
from typing import Optional, List, Callable, Any
from collections import OrderedDict
from threading import Lock

logger = logging.getLogger("EmbeddingCache")


class EmbeddingCache:
    """
    Thread-safe LRU cache for embedding vectors.
    
    Features:
    - Fixed size with LRU eviction
    - Thread-safe access
    - Cache stats for monitoring
    - TTL support (optional)
    """
    
    DEFAULT_MAX_SIZE = 256
    DEFAULT_TTL_SECONDS = 3600  # 1 hour
    
    def __init__(self, max_size: int = DEFAULT_MAX_SIZE, ttl_seconds: int = DEFAULT_TTL_SECONDS):
        self._cache: OrderedDict[str, tuple] = OrderedDict()  # key -> (vector, timestamp)
        self._max_size = max_size
        self._ttl = ttl_seconds
        self._lock = Lock()
        
        # Stats
        self._hits = 0
        self._misses = 0
        self._evictions = 0
    
    def _make_key(self, text: str, model_name: str = "default") -> str:
        """Create a cache key from text and model name."""
        # Use hash to handle very long texts
        text_hash = hashlib.md5(text.encode('utf-8')).hexdigest()
        return f"{model_name}:{text_hash}"
    
    def get(self, text: str, model_name: str = "default") -> Optional[List[float]]:
        """
        Get cached embedding if exists and not expired.
        
        Args:
            text: The text that was embedded
            model_name: Name of embedding model (for key uniqueness)
            
        Returns:
            Cached vector or None if not found/expired
        """
        key = self._make_key(text, model_name)
        
        with self._lock:
            if key not in self._cache:
                self._misses += 1
                return None
            
            vector, timestamp = self._cache[key]
            
            # Check TTL
            if time.time() - timestamp > self._ttl:
                del self._cache[key]
                self._misses += 1
                return None
            
            # Move to end (LRU touch)
            self._cache.move_to_end(key)
            self._hits += 1
            return vector
    
    def put(self, text: str, vector: List[float], model_name: str = "default"):
        """
        Store an embedding in cache.
        
        Args:
            text: The text that was embedded
            vector: The embedding vector
            model_name: Name of embedding model
        """
        key = self._make_key(text, model_name)
        
        with self._lock:
            # If already exists, update and move to end
            if key in self._cache:
                self._cache[key] = (vector, time.time())
                self._cache.move_to_end(key)
                return
            
            # Evict oldest if at capacity
            while len(self._cache) >= self._max_size:
                self._cache.popitem(last=False)
                self._evictions += 1
            
            self._cache[key] = (vector, time.time())
    
    def get_or_compute(
        self, 
        text: str, 
        compute_fn: Callable[[str], List[float]],
        model_name: str = "default"
    ) -> List[float]:
        """
        Get from cache or compute and cache.
        
        Args:
            text: Text to embed
            compute_fn: Function to compute embedding if not cached
            model_name: Name of embedding model
            
        Returns:
            Embedding vector (from cache or freshly computed)
        """
        cached = self.get(text, model_name)
        if cached is not None:
            return cached
        
        # Compute
        vector = compute_fn(text)
        self.put(text, vector, model_name)
        return vector
    
    def clear(self):
        """Clear all cached embeddings."""
        with self._lock:
            self._cache.clear()
            logger.info("🗑️ Embedding cache cleared")
    
    def get_stats(self) -> dict:
        """Get cache statistics."""
        with self._lock:
            total = self._hits + self._misses
            hit_rate = (self._hits / total * 100) if total > 0 else 0
            
            return {
                "size": len(self._cache),
                "max_size": self._max_size,
                "hits": self._hits,
                "misses": self._misses,
                "evictions": self._evictions,
                "hit_rate": f"{hit_rate:.1f}%",
            }
    
    def log_stats(self):
        """Log cache statistics."""
        stats = self.get_stats()
        logger.info(
            f"📊 EmbeddingCache: "
            f"{stats['size']}/{stats['max_size']} entries, "
            f"{stats['hit_rate']} hit rate, "
            f"{stats['hits']} hits, {stats['misses']} misses"
        )


# Global instance
_cache: Optional[EmbeddingCache] = None


def get_embedding_cache() -> EmbeddingCache:
    """Get or create the global embedding cache."""
    global _cache
    if _cache is None:
        _cache = EmbeddingCache()
        logger.info("⚡ EmbeddingCache initialized (max_size=256, ttl=3600s)")
    return _cache


def get_embedding_cached(
    text: str, 
    model: Any,
    model_name: str = "default"
) -> List[float]:
    """
    Convenience function to get cached embedding.
    
    Args:
        text: Text to embed
        model: Embedding model with .encode() method
        model_name: Model identifier for cache key
        
    Returns:
        Embedding vector
    """
    cache = get_embedding_cache()
    
    def compute(t: str) -> List[float]:
        return model.encode(t).tolist()
    
    return cache.get_or_compute(text, compute, model_name)


def get_cache_stats() -> dict:
    """Get cache statistics."""
    return get_embedding_cache().get_stats()
