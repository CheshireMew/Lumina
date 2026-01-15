import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from core.db.interface import VectorDBInterface

logger = logging.getLogger("memory.vector_store")

class VectorStore:
    """
    Manages 'episodic_memory' using a VectorDBInterface driver.
    Database-agnostic implementation.
    """

    def __init__(self, driver: VectorDBInterface):
        self.driver = driver

    async def add_episodic_memory(self, 
                                  character_id: str, 
                                  content: str, 
                                  embedding: List[float],
                                  status: str = "active") -> str:
        """Add processed memory to episodic_memory table"""
        try:
            data = {
                "character_id": character_id.lower(),
                "content": content,
                "embedding": embedding,
                "created_at": datetime.now().isoformat(),
                "status": status,
                "batch_id": None,
                "hit_count": 0,
                "last_hit_at": None
            }
            return await self.driver.create("episodic_memory", data)
        except Exception as e:
            logger.error(f"鉂?Error adding episodic memory: {e}")
            raise

    async def search(self, 
                    query_vector: List[float], 
                    character_id: str, 
                    limit: int = 10, 
                    threshold: float = 0.6,
                    target_table: str = "episodic_memory") -> List[Dict]:
        """Vector Search (Delegated to Driver)"""
        try:
            filters = {"character_id": character_id}
            if target_table == "episodic_memory":
                filters["status"] = "active"
                
            return await self.driver.search_vector(
                table=target_table,
                vector=query_vector,
                limit=limit,
                threshold=threshold,
                filter_criteria=filters
            )
        except Exception as e:
            logger.error(f"Vector search error: {e}")
            return []

    async def search_fulltext(self, 
                              query: str, 
                              character_id: str, 
                              limit: int = 10,
                              target_table: str = "episodic_memory") -> List[Dict]:
        """Full-Text Search (Delegated to Driver)"""
        try:
            filters = {"character_id": character_id}
            if target_table == "episodic_memory":
                 filters["status"] = "active"
                 
            # Fields ignored by current driver impl but good to pass for future
            fields = ["content"] if target_table == "episodic_memory" else ["narrative"]
            
            return await self.driver.search_fulltext(
                table=target_table,
                query=query,
                limit=limit,
                fields=fields,
                filter_criteria=filters
            )
        except Exception as e:
            logger.error(f"鉂?Full-text search error: {e}")
            return []

    async def search_hybrid(self, 
                           query: str,
                           query_vector: List[float],
                           character_id: str,
                           limit: int = 10,
                           vector_weight: float = 0.4,
                           initial_threshold: float = 0.45,
                           min_results: int = 3,
                           target_table: str = "episodic_memory") -> List[Dict]:
        """Hybrid Search (Delegated to Driver)"""
        try:
            filters = {"character_id": character_id}
            if target_table == "episodic_memory":
                filters["status"] = "active"

            results = []
            current_threshold = initial_threshold
            
            # Gradient Degradation Loop
            # If not enough results, lower threshold and retry up to 3 times
            for attempt in range(3):
                results = await self.driver.search_hybrid(
                    query=query,
                    vector=query_vector,
                    table=target_table,
                    limit=limit,
                    threshold=current_threshold,
                    vector_weight=vector_weight,
                    filter_criteria=filters
                )
                
                if len(results) >= min_results:
                    break
                    
                if current_threshold <= 0.25: # Safety floor
                    break
                    
                logger.info(f"📉 Hybrid Search: Not enough results ({len(results)}/{min_results}). Lowering threshold {current_threshold:.2f} -> {current_threshold - 0.1:.2f}")
                current_threshold -= 0.1
            
            # Optimization: Mark hits
            if results:
                memory_ids = [str(r.get('id')) for r in results if r.get('id')]
                if memory_ids:
                     await self.driver.mark_memories_hit(memory_ids)
                     
            return results
        except Exception as e:
            logger.error(f"鉂?Hybrid search error: {e}")
            return []

