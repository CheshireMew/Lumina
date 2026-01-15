from abc import ABC, abstractmethod
from typing import List, Dict, Any, Optional

class VectorDBInterface(ABC):
    """
    Abstract Interface for Vector Database Operations.
    Decouples business logic (VectorStore) from specific DB implementations (SurrealDB, Postgres, etc).
    """

    @abstractmethod
    async def connect(self):
        """Establish connection to the database."""
        pass

    @abstractmethod
    async def close(self):
        """Close connection."""
        pass
        
    @abstractmethod
    async def initialize_schema(self):
        """
        Initialize necessary tables, indexes, and extensions.
        Each driver must handle its own DDL.
        """
        pass

    @abstractmethod
    async def create(self, table: str, data: Dict[str, Any]) -> str:
        """Insert data and return ID."""
        pass

    @abstractmethod
    async def update(self, table: str, id: str, data: Dict[str, Any]) -> bool:
        """Update existing record (Merge strategy)."""
        pass
    
    @abstractmethod
    async def delete(self, table: str, id: str) -> bool:
        """Delete a record."""
        pass

    @abstractmethod
    async def mark_memories_hit(self, memory_ids: List[str]):
        """
        Specialized method to increment hit counts/update last_access.
        Optimization: Drivers can implement batch updates here.
        """
        pass

    @abstractmethod
    async def search_vector(self, 
                          table: str, 
                          vector: list, 
                          limit: int, 
                          threshold: float,
                          filter_criteria: Optional[Dict] = None) -> list:
        """Vector similarity search."""
        pass

    @abstractmethod
    async def search_fulltext(self, 
                            table: str, 
                            query: str, 
                            limit: int,
                            fields: Optional[List[str]] = None,
                            filter_criteria: Optional[Dict] = None) -> list:
        """Full text / Substring search."""
        pass
    
    @abstractmethod
    async def search_hybrid(self,
                          query: str,
                          vector: list,
                          table: str,
                          limit: int,
                          threshold: float,
                          vector_weight: float = 0.5,
                          filter_criteria: Optional[Dict] = None) -> list:
         """
         Hybrid search (Vector + FullText).
         Drivers can implement native hybrid (like SurrealDB/Elastic) 
         or fall back to RRF fusion if needed.
         """
         pass
