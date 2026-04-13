"""
Memory Module
=============

Memory system functionality.

Example:
    await lumina.memory.store("User likes blue")
    memories = await lumina.memory.search("What color does the user like")
"""

import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass

from ..errors import DriverError
from ..utils import get_service_or_raise, driver_error_handler

logger = logging.getLogger("Lumina.SDK.Memory")


@dataclass
class MemoryItem:
    """Memory entry"""
    id: str
    content: str
    tags: List[str] = None
    score: float = 1.0
    timestamp: str = ""
    metadata: Dict[str, Any] = None


class MemoryModule:
    """
    Memory system module
    
    Methods:
        store(content, **kwargs) - Store memory
        search(query, limit) - Search memory
        get_chat_history(limit) - Get chat history
    """
    
    def __init__(self, container):
        self._container = container
    
    def _get_memory_service(self):
        """Get memory service or raise DriverError if unavailable."""
        return get_service_or_raise(self._container, 'memory', 'Memory')
    
    @driver_error_handler("Memory", "store")
    async def store(
        self,
        content: str,
        *,
        tags: List[str] = None,
        importance: float = 0.5,
        metadata: Dict[str, Any] = None,
        **kwargs
    ) -> str:
        """
        Store memory
        
        Args:
            content: Memory content
            tags: Tag list
            importance: Importance (0.0-1.0)
            metadata: Additional metadata
        
        Returns:
            Memory ID
        
        Example:
            id = await lumina.memory.store(
                "User likes blue",
                tags=["preference", "color"]
            )
        """
        memory_service = self._get_memory_service()
        
        if hasattr(memory_service, 'store'):
            result = await memory_service.store(
                content=content,
                tags=tags or [],
                importance=importance,
                metadata=metadata or {},
                **kwargs
            )
            return result if isinstance(result, str) else str(result)
        elif hasattr(memory_service, 'add'):
            result = await memory_service.add(content, tags=tags)
            return str(result)
        else:
            raise DriverError("Memory service does not support store method")
    
    @driver_error_handler("Memory", "search")
    async def search(
        self,
        query: str,
        *,
        limit: int = 5,
        tags: List[str] = None,
        threshold: float = 0.5,
        **kwargs
    ) -> List[MemoryItem]:
        """
        Search memory
        
        Args:
            query: Search query
            limit: Maximum return count
            tags: Filter tags
            threshold: Similarity threshold
        
        Returns:
            List of matching memories
        
        Example:
            memories = await lumina.memory.search("What color does the user like")
            for mem in memories:
                print(mem.content)
        """
        memory_service = self._get_memory_service()
        
        if hasattr(memory_service, 'search'):
            results = await memory_service.search(
                query=query,
                limit=limit,
                tags=tags,
                threshold=threshold,
                **kwargs
            )
            return [
                MemoryItem(
                    id=r.get("id", ""),
                    content=r.get("content", r.get("text", "")),
                    tags=r.get("tags", []),
                    score=r.get("score", r.get("similarity", 1.0)),
                    metadata=r.get("metadata", {})
                )
                for r in results
            ]
        elif hasattr(memory_service, 'query'):
            results = await memory_service.query(query, top_k=limit)
            return [
                MemoryItem(id=str(i), content=r, tags=[])
                for i, r in enumerate(results)
            ]
        else:
            raise DriverError("Memory service does not support search method")
    
    async def get_chat_history(self, limit: int = 20) -> List[Dict[str, str]]:
        """
        Get chat history
        
        Args:
            limit: Maximum return count
        
        Returns:
            List of chat messages [{"role": "user", "content": "..."}]
        """
        memory_service = getattr(self._container, 'memory', None)
        if not memory_service:
            return []
        
        try:
            if hasattr(memory_service, 'get_chat_history'):
                return await memory_service.get_chat_history(limit=limit)
            elif hasattr(memory_service, 'get_history'):
                return await memory_service.get_history(limit=limit)
            return []
        except Exception as e:
            logger.warning(f"Failed to get chat history: {e}")
            return []
    
    async def clear(self, tags: List[str] = None) -> int:
        """
        Clear memory
        
        Args:
            tags: Only clear memories with specified tags, None means clear all
        
        Returns:
            Number of deleted memories
        """
        memory_service = getattr(self._container, 'memory', None)
        if not memory_service:
            return 0
        
        try:
            if hasattr(memory_service, 'clear'):
                return await memory_service.clear(tags=tags)
            return 0
        except Exception as e:
            logger.error(f"Failed to clear memory: {e}")
            return 0

