import logging
from typing import List, Dict, Any, Optional
from datetime import datetime
from memory.connection import DBConnection

logger = logging.getLogger("memory.vector_store")

class VectorStore:
    """
    Manages 'episodic_memory' table (Vector + FullText Search).
    """

    def __init__(self):
        # DBConnection is valid singleton
        pass

    async def _get_db(self):
        return await DBConnection.get_db()

    def _parse_query_result(self, res) -> List[Dict]:
        """Robust parser for SurrealDB results"""
        if not res: return []
        if isinstance(res, dict):
            if 'result' in res:
                val = res['result']
                return val if isinstance(val, list) else [val]
            return [res]
        if isinstance(res, list):
            first = res[0]
            if isinstance(first, dict):
                if 'result' in first:
                    val = first['result']
                    return val if val else []
                return res
        return []

    async def add_episodic_memory(self, 
                                  character_id: str, 
                                  content: str, 
                                  embedding: List[float],
                                  status: str = "active") -> str:
        """Add processed memory to episodic_memory table"""
        db = await self._get_db()
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
            results = await db.create("episodic_memory", data)
            
            if not results: raise ValueError("Create returned empty result")
            return self._extract_id(results)
        except Exception as e:
            logger.error(f"❌ Error adding episodic memory: {e}")
            raise

    def _extract_id(self, results) -> str:
        if hasattr(results, 'id'): return str(results.id)
        if isinstance(results, dict) and 'id' in results: return str(results['id'])
        if isinstance(results, list) and len(results) > 0:
            first = results[0]
            if hasattr(first, 'id'): return str(first.id)
            if isinstance(first, dict) and 'id' in first: return str(first['id'])
        return str(results)

    async def _mark_memories_hit(self, memory_ids: List[str]):
        """Increment hit count for memories"""
        db = await self._get_db()
        for mem_id in memory_ids:
            try:
                await db.query(f"""
                    UPDATE {mem_id} SET 
                        hit_count = (hit_count ?? 0) + 1,
                        last_hit_at = time::now()
                """)
            except Exception as e:
                logger.warning(f"Failed to mark hit {mem_id}: {e}")

    async def search(self, 
                    query_vector: List[float], 
                    character_id: str, 
                    limit: int = 10, 
                    threshold: float = 0.6,
                    target_table: str = "episodic_memory") -> List[Dict]:
        """Vector Search (HNSW)"""
        db = await self._get_db()
        try:
            # Note: conversation_log may not have 'status' or 'hit_count' fields
            # We construct query dynamically based on table
            status_clause = "AND status = 'active'" if target_table == "episodic_memory" else ""
            
            # Select relevant fields based on table
            fields = "id, content, status, created_at, hit_count" if target_table == "episodic_memory" else "id, narrative as content, created_at"
            
            query = f"""
            SELECT 
                {fields},
                vector::similarity::cosine(embedding, $query_vec) AS score 
            FROM {target_table} 
            WHERE character_id = $character_id
              {status_clause}
              AND vector::similarity::cosine(embedding, $query_vec) > $threshold
            ORDER BY score DESC 
            LIMIT $limit;
            """
            return self._parse_query_result(await db.query(query, {
                "query_vec": query_vector,
                "character_id": character_id,
                "limit": limit,
                "threshold": threshold
            }))
        except Exception as e:
            logger.error(f"❌ Vector search error: {e}")
            return []

    async def search_fulltext(self, 
                              query: str, 
                              character_id: str, 
                              limit: int = 10,
                              target_table: str = "episodic_memory") -> List[Dict]:
        """Full-Text Search (Substring match)"""
        db = await self._get_db()
        try:
            status_clause = "AND status = 'active'" if target_table == "episodic_memory" else ""
            fields = "id, content, status, created_at" if target_table == "episodic_memory" else "id, narrative as content, created_at"
            search_field = "content" if target_table == "episodic_memory" else "narrative"

            sql = f"""
            SELECT {fields}, 1.0 AS relevance 
            FROM {target_table}
            WHERE string::lowercase({search_field}) CONTAINS string::lowercase($query)
              AND character_id = $character_id
              {status_clause}
            ORDER BY created_at DESC
            LIMIT $limit;
            """
            return self._parse_query_result(await db.query(sql, {
                "query": query,
                "character_id": character_id,
                "limit": limit
            }))
        except Exception as e:
            logger.error(f"❌ Full-text search error: {e}")
            return []

    async def search_hybrid(self, 
                           query: str,
                           query_vector: List[float],
                           character_id: str,
                           limit: int = 10,
                           vector_weight: float = 0.4,
                           initial_threshold: float = 0.6,
                           min_results: int = 3,
                           target_table: str = "episodic_memory") -> List[Dict]:
        """Hybrid Search with Adaptive Threshold & RRF"""
        current_threshold = initial_threshold
        step_c = 0.1
        min_threshold = 0.2
        final_results = []
        
        for _ in range(5): # Max 5 loops
            vec_results = await self.search(
                query_vector, character_id, limit * 2, 
                threshold=current_threshold, target_table=target_table
            )
            text_results = await self.search_fulltext(
                query, character_id, limit * 2, target_table=target_table
            )
            
            # RRF Fusion
            scores = {}
            items = {}
            k = 60
            
            def process_list(lst, weight):
                for rank, item in enumerate(lst):
                    if not isinstance(item, dict): continue
                    item_id = str(item.get('id', rank))
                    if item_id not in scores:
                        scores[item_id] = 0
                        items[item_id] = item
                    scores[item_id] += weight / (k + rank + 1)

            process_list(vec_results, vector_weight)
            process_list(text_results, 1.0 - vector_weight)
            
            sorted_ids = sorted(scores.keys(), key=lambda x: scores[x], reverse=True)
            results = []
            for item_id in sorted_ids[:limit]:
                item = items[item_id]
                item['hybrid_score'] = scores[item_id]
                results.append(item)
            
            final_results = results
            
            if len(final_results) >= min_results:
                break
            if current_threshold <= min_threshold:
                break
                
            current_threshold = max(min_threshold, current_threshold - step_c)
            
        if final_results:
            memory_ids = [str(r.get('id')) for r in final_results if r.get('id')]
            if memory_ids:
                await self._mark_memories_hit(memory_ids)
        
        return final_results
