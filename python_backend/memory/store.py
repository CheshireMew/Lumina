import logging
from datetime import datetime, timezone
from typing import Dict, List

from core.db.interface import VectorDBInterface

logger = logging.getLogger("memory.store")


class MemoryItemStore:
    """Storage adapter for the single long-term memory table."""

    table_name = "memory_items"

    def __init__(self, driver: VectorDBInterface):
        self._driver = driver

    @property
    def driver(self) -> VectorDBInterface:
        return self._driver

    def replace_driver(self, driver: VectorDBInterface):
        self._driver = driver

    async def create_memory_item(
        self,
        *,
        character_id: str,
        content: str,
        embedding: List[float] | None = None,
        scope: str = "relationship",
        memory_type: str = "episode",
        subject_id: str | None = None,
        summary: str | None = None,
        source_turn_ids: list[str] | None = None,
        confidence: float = 1.0,
        importance: float = 1.0,
        metadata: Dict | None = None,
    ) -> str:
        data = {
            "character_id": character_id.lower(),
            "scope": scope,
            "memory_type": memory_type,
            "subject_id": subject_id,
            "content": content,
            "summary": summary,
            "embedding": embedding,
            "source_turn_ids": source_turn_ids or [],
            "confidence": confidence,
            "importance": importance,
            "status": "active",
            "created_at": datetime.now(timezone.utc),
            "updated_at": datetime.now(timezone.utc),
            "metadata": metadata or {},
        }
        return await self.driver.create(self.table_name, data)

    async def search_vector(
        self,
        *,
        query_vector: List[float],
        character_id: str,
        limit: int = 10,
        threshold: float = 0.6,
        memory_types: list[str] | None = None,
    ) -> List[Dict]:
        try:
            filters = self._filters(character_id, memory_types)
            return await self.driver.search_vector(
                table=self.table_name,
                vector=query_vector,
                limit=limit,
                threshold=threshold,
                filter_criteria=filters,
            )
        except Exception as exc:
            logger.error("Memory vector search failed: %s", exc)
            return []

    async def search_fulltext(
        self,
        *,
        query: str,
        character_id: str,
        limit: int = 10,
        memory_types: list[str] | None = None,
    ) -> List[Dict]:
        try:
            filters = self._filters(character_id, memory_types)
            return await self.driver.search_fulltext(
                table=self.table_name,
                query=query,
                limit=limit,
                fields=["content"],
                filter_criteria=filters,
            )
        except Exception as exc:
            logger.error("Memory full-text search failed: %s", exc)
            return []

    async def search_hybrid(
        self,
        *,
        query: str,
        query_vector: List[float],
        character_id: str,
        limit: int = 10,
        vector_weight: float = 0.4,
        initial_threshold: float = 0.45,
        min_results: int = 3,
        memory_types: list[str] | None = None,
    ) -> List[Dict]:
        try:
            filters = self._filters(character_id, memory_types)
            results = []
            current_threshold = initial_threshold

            for _ in range(3):
                results = await self.driver.search_hybrid(
                    query=query,
                    vector=query_vector,
                    table=self.table_name,
                    limit=limit,
                    threshold=current_threshold,
                    vector_weight=vector_weight,
                    filter_criteria=filters,
                )

                if len(results) >= min_results or current_threshold <= 0.25:
                    break
                current_threshold -= 0.1

            memory_ids = [str(item.get("id")) for item in results if item.get("id")]
            if memory_ids:
                await self.driver.mark_memories_hit(memory_ids)
            return results
        except Exception as exc:
            logger.error("Memory hybrid search failed: %s", exc)
            return []

    def _filters(self, character_id: str, memory_types: list[str] | None = None) -> Dict:
        filters: Dict = {
            "character_id": character_id,
            "status": "active",
        }
        if memory_types and len(memory_types) == 1:
            filters["memory_type"] = memory_types[0]
        return filters
