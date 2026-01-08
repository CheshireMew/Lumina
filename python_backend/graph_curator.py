import logging
import asyncio
from datetime import datetime

logger = logging.getLogger("graph_curator")
logging.basicConfig(level=logging.INFO)

class GraphCurator:
    """
    The Gardener of the Knowledge Graph.
    Responsible for periodic maintenance:
    1. Pruning weak (forgotten) memories.
    2. Detecting conflicts (TODO).
    3. Optimizing structure (TODO).
    """
    def __init__(self, surreal_memory, hippocampus=None):
        self.memory = surreal_memory
        self.hippo = hippocampus
        self.rules = self._load_rules()
        
    def _load_rules(self):
        import json
        import os
        try:
            path = os.path.join(os.path.dirname(__file__), "config", "relation_rules.json")
            if os.path.exists(path):
                with open(path, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load rules: {e}")
        return {"opposites": []}
        
    async def run_maintenance(self):
        """Run all maintenance tasks."""
        logger.info("🌿 Starting Graph Curation...")
        try:
            # 1. Pruning
            count = await self.prune_weak_memories()
            logger.info(f"🌿 Pruned {count} weak edges.")
            
            # 2. Conflict Resolution
            if self.hippo and self.rules.get("opposites"):
                conflicts = await self.detect_and_resolve_conflicts()
                logger.info(f"⚔️ Resolved {conflicts} conflicts.")
                
        except Exception as e:
            logger.error(f"🌿 Maintenance failed: {e}")

    async def detect_and_resolve_conflicts(self) -> int:
        """
        Detect conflicts using Hybrid Strategy:
        1. Hard Constraint (Exclusive Relations) -> Rule Based
        2. Soft Constraint (Semantic Overlap) -> Vector Clustering + Batch LLM
        """
        if not self.memory.db: return 0
        
        resolved_count = 0
        
        # --- Phase 1: Hard Constraints (Exclusive) ---
        # [DISABLED Request by User: Rely on Natural Decay]
        """
        exclusives = self.rules.get("exclusive", [])
        for rel in exclusives:
            try:
                await self.memory.db.query(f"DEFINE TABLE {rel} SCHEMALESS PERMISSIONS FULL;")
                
                # Check for violations
                q = f"SELECT in, count() as c FROM {rel} GROUP BY in"
                res = await self.memory.db.query(q)
                
                groups = []
                if res and isinstance(res, list) and isinstance(res[0], dict) and 'result' in res[0]:
                    groups = res[0]['result']
                
                for group in groups:
                    if group.get('c', 0) > 1:
                        subj = group['in']
                        # Fetch ALL candidates
                        q_edges = f"SELECT id, in, out, base_strength, context, last_mentioned, created_at FROM {rel} WHERE in='{subj}'"
                        res_e = await self.memory.db.query(q_edges)
                        
                        edges = []
                        if res_e and isinstance(res_e, list) and isinstance(res_e[0], dict) and 'result' in res_e[0]:
                            edges = res_e[0]['result']
                            
                        if len(edges) < 2: continue
                        
                        logger.info(f"⚔️ Conflict (Exclusive): {rel} for {subj} has {len(edges)} candidates. Arbitrating deterministically...")
                        
                        # Deterministic Strategy: Keep Latest -> Strongest
                        # Sort by last_mentioned DESC, then base_strength DESC
                        def sort_key(e):
                            ts = e.get('last_mentioned') or e.get('created_at') or "1970-01-01"
                            # Convert to str for simple sort, or parse if needed. 
                            # ISO string comparison works for standard format.
                            return (ts, e.get('base_strength', 0))
                            
                        edges.sort(key=sort_key, reverse=True)
                        
                        winner = edges[0]
                        losers = edges[1:]
                        
                        logger.info(f"👑 Winner: {winner['id']} ({winner.get('context', 'No ctx')})")
                        
                        # Delete losers
                        c_del = 0
                        for loser in losers:
                            try:
                                await self.memory.db.delete(loser['id'])
                                c_del += 1
                            except: pass
                        resolved_count += c_del

            except Exception as e:
                logger.warning(f"Error checking exclusive {rel}: {e}")
        """

        # --- Phase 2: Soft Constraints (Semantic Clustering) ---
        # [DISABLED Request by User: Rely on Natural Decay for now]
        # We look for edges that talk about the same 'Topic' but might contradict.
        # Strict Vector Search: Cosine Similarity > 0.85
        """
        try:
            # 1. Get all subjects that have edges with embeddings
            # (Limitation: This scans all entities. For production, use dirty flags or time-window)
            # For now, we sample recent entities or just heavily active ones.
            # Simplified: Iterate Top 50 entities by activity? 
            # Or just 'SELECT distinct in FROM emotion, thought, ...' (Too many tables).
            
            # Alternative: We scan 'facts_staging' or just rely on 'entity' table loop?
            # Let's try iterating 'entity' table (Assuming < 1000 entities for now)
            q_ent = "SELECT id FROM entity LIMIT 100" 
            res_ent = await self.memory.db.query(q_ent)
            
            entities = []
            if res_ent and isinstance(res_ent, list) and res_ent[0].get('result'):
                entities = res_ent[0]['result']
                
            import numpy as np
            
            for ent in entities:
                ent_id = ent['id']
                
                # Fetch ALL outgoing edges with embeddings for this entity
                # This requires querying ALL relationship tables? SurrealDB is graph, but we need to know table names.
                # We can query `SELECT * FROM ->? WHERE embedding != NONE` (SurrealQL nice feature!)
                # "SELECT * FROM ->? WHERE embedding != NONE" might work if edges are directed.
                
                q_edges = f"SELECT id, context, embedding, base_strength, last_mentioned FROM ->? WHERE out != {ent_id} AND embedding != NONE;"
                # Wait, ->? selects edges outgoing from {ent_id}? No, standard SQL doesn't support wildcard table.
                # SurrealDB implementation of "SELECT * FROM ->" is implied if we start from record?
                # "SELECT ->? FROM {ent_id}"?
                
                # Safer: We iterate known relation types? Or just skip this phase if too complex for generic SQL.
                # Let's fallback to: We rely on the `relation_rules` to know which tables to scan?
                # Or we hardcode common subjective tables: LIKES, HATES, OPINION, BELIEVES.
                
                soft_tables = ["LIKES", "HATES", "DISLIKES", "LOVES", "TRUSTS", "DISTRUSTS", "OPINION"]
                
                all_edges = []
                for tbl in soft_tables:
                    try:
                        q_t = f"SELECT id, context, embedding, base_strength, last_mentioned, type::string($table) as type FROM {tbl} WHERE in='{ent_id}' AND embedding != NONE"
                        res_t = await self.memory.db.query(q_t, {"table": tbl})
                        if res_t and res_t[0].get('result'):
                            all_edges.extend(res_t[0]['result'])
                    except: pass
                    
                if len(all_edges) < 2: continue
                
                # Cluster
                clusters = self._cluster_edges(all_edges)
                
                for cluster in clusters:
                    if len(cluster) > 1:
                        # Found a semantic topic cluster for this person
                        logger.info(f"⚔️ Conflict (Semantic): {ent_id} has {len(cluster)} edges on similar topic.")
                        decision = await self._arbitrate_batch_with_llm(cluster, "Semantic Cluster")
                        resolved_count += await self._execute_batch_decision(decision)

        except Exception as e:
            logger.warning(f"Error in Semantic clustering: {e}")
        """
                
        return resolved_count

    def _cluster_edges(self, edges, threshold=0.85):
        """Greedy clustering of edges based on embedding similarity."""
        import numpy as np
        
        clusters = []
        # edges format: [{'id':..., 'embedding': [...]}, ...]
        
        # 1. Normalize vectors? Assuming model outputs normalized.
        # 2. Greedy Loop
        pool = edges.copy()
        
        while pool:
            seed = pool.pop(0)
            seed_vec = np.array(seed['embedding'])
            current_cluster = [seed]
            
            # Find neighbors in remaining pool
            non_neighbors = []
            for candidate in pool:
                cand_vec = np.array(candidate['embedding'])
                # Cosine Sim
                sim = np.dot(seed_vec, cand_vec) / (np.linalg.norm(seed_vec) * np.linalg.norm(cand_vec) + 1e-9)
                
                if sim >= threshold:
                    current_cluster.append(candidate)
                else:
                    non_neighbors.append(candidate)
            
            clusters.append(current_cluster)
            pool = non_neighbors
            
        return clusters

    async def _execute_batch_decision(self, decision):
        c = 0
        if not decision: return 0
        to_delete = decision.get("delete", [])
        for del_id in to_delete:
            try:
                await self.memory.db.delete(del_id)
                c += 1
            except: pass
        return c

    async def _arbitrate_batch_with_llm(self, edges, rel_type):
        """
        Arbitrate a list of conflicting edges in ONE go.
        Returns: Dict {"keep": [id1], "delete": [id2, id3]}
        """
        import requests
        import json
        
        edges_desc = []
        for i, edge in enumerate(edges):
            edges_desc.append(f"""
            ID: {edge['id']}
            Context: "{edge.get('context', 'Unknown')}"
            Time: {edge.get('last_mentioned', 'Unknown')}
            Strength: {edge.get('base_strength', 0)}
            """)
        
        prompt = f"""
        You are the Memory Arbitrator for an AI.
        You have detected {len(edges)} semantically related ('{rel_type}') relationships for the same entity.
        
        Candidates:
        {"".join(edges_desc)}
        
        Task:
        1. **Deduplicate**: If multiple facts convey substantially the same information (e.g., "Likes X" and "Loves X"), keep ONLY the most precise/strongest one. Mark the redundant weaker ones for deletion.
        2. **Resolve Conflicts**: If facts contradict (e.g., "Hates X" and "Loves X"), determine the truth based on recency and context. Mark false/outdated facts for deletion.
        3. **Consolidate**: If facts are complementary, keep them.
        
        Output JSON ONLY:
        {{
            "keep": ["ID_of_edge_to_keep", ...],
            "delete": ["ID_of_edge_to_delete", ...]
        }}
        """
        
        try:
            payload = {
                "model": self.hippo.model,
                "messages": [{"role": "system", "content": "Output JSON only."}, {"role": "user", "content": prompt}],
                "temperature": 0.0,
                "response_format": {"type": "json_object"}
            }
            headers = {"Authorization": f"Bearer {self.hippo.api_key}"}
            
            url = f"{self.hippo.base_url}/chat/completions"
            resp = requests.post(url, json=payload, headers=headers, timeout=20)
            
            if resp.status_code == 200:
                data = resp.json()
                content = data['choices'][0]['message']['content']
                decision = json.loads(content)
                logger.info(f"🤖 Batch Arbitration Decision: {decision}")
                return decision
        except Exception as e:
            logger.error(f"Batch Arbitration Error: {e}")
            
        return {"keep": [], "delete":[]}
        
    async def prune_weak_memories(self) -> int:
        """Delete edges that have decayed below the survival threshold (0.05)."""
        if not self.memory.db:
             logger.warning("DB not connected, skipping pruning.")
             return 0
             
        pruned_count = 0
        try:
            # 1. Get all tables
            info = await self.memory.db.query("INFO FOR DB;")
            # Structure: [{'result': {'tables': {...}, ...}, 'status': 'OK'}]
            if not info or not info[0].get('result'):
                return 0
                
            tables = info[0]['result'].get('tables', {})
            
            excluded = ['conversation', 'entity', 'audit', 'facts_staging', 'migrations']
            
            for table_name in tables:
                if table_name in excluded: 
                    continue
                
                # Optimistically try to delete based on edge decay logic
                # If table doesn't have in/out or strength, query might just affect nothing or fail gracefully
                # We check 'in != NONE' to ensure we only touch likely-edge tables
                
                q = f"""
                DELETE FROM {table_name} 
                WHERE 
                    ((base_strength OR 0.8) * math::pow(0.99, duration::days(time::now() - (last_mentioned OR created_at)))) < 0.05
                    AND in != NONE 
                    AND out != NONE
                RETURN BEFORE;
                """
                
                res = await self.memory.db.query(q)
                
                if res and isinstance(res, list) and res[0].get('result'):
                     deleted_items = res[0]['result']
                     count = len(deleted_items)
                     if count > 0:
                         logger.info(f"🌿 Pruned {count} items from '{table_name}'")
                         pruned_count += count
                     
            return pruned_count
            
        except Exception as e:
            logger.error(f"Pruning logic error: {e}")
            return 0
