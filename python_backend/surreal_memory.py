import logging
import json
import asyncio
from typing import List, Dict, Optional, Any
from surrealdb import Surreal, AsyncSurreal

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SurrealMemory:
    def __init__(self, url: str = "ws://127.0.0.1:8000/rpc", user: str = "root", password: str = "root", db_namespace: str = "lumina", db_name: str = "memory"):
        self.url = url
        self.user = user
        self.password = password
        self.namespace = db_namespace
        self.database = db_name
        self.db: Optional[AsyncSurreal] = None

    async def connect(self):
        """Establish connection to SurrealDB."""
        try:
            self.db = AsyncSurreal(self.url)
            await self.db.connect()
            await self.db.signin({"username": self.user, "password": self.password})
            await self.db.use(self.namespace, self.database)
            logger.info("✅ Connected to SurrealDB")
            
            # Initialize schema
            await self._initialize_schema()
        except Exception as e:
            logger.error(f"❌ Failed to connect to SurrealDB: {e}")
            raise

    async def _initialize_schema(self):
        """Define tables and indexes."""
        if not self.db:
            return

        try:
            # 1. Nodes (Schemaless is fine, but we define for clarity)
            # character, user, fact
            
            # 2. Vector Index on 'fact'
            # Using HNSW for performance
            # Dimension 384 (all-MiniLM-L6-v2)
            await self.db.query("DEFINE TABLE fact SCHEMALESS;")
            await self.db.query("DEFINE INDEX fact_embedding ON fact FIELDS embedding HNSW DIMENSION 384 DIST COSINE;")
            
            logger.info("✅ Schema initialized")
        except Exception as e:
            logger.error(f"⚠️ Schema initialization warning: {e}")

    async def add_memory(self, 
                        content: str, 
                        embedding: List[float], 
                        agent_id: str, 
                        user_id: str = "user_default",
                        importance: int = 1,
                        emotion: Optional[str] = None):
        """
        Add a new memory fact and link it to the character and user.
        
        Graph Structure:
        (character) -[observes]-> (fact)
        (fact) -[about]-> (user)
        """
        if not self.db:
            await self.connect()

        try:
            # 1. Create Fact Node
            fact_data = {
                "text": content,
                "embedding": embedding,
                "importance": importance,
                "emotion": emotion,
                "created_at": "time::now()",  # SurrealDB function
                "channel": "character" # Legacy tag compatibility
            }
            # Create returns a list of results, we take the first one
            fact_results = await self.db.create("fact", fact_data)
            logger.info(f"DEBUG: fact_results type={type(fact_results)} val={fact_results}")
            
            if not fact_results:
                raise ValueError("Create returned empty result")

            # Robust parsing:
            # 1. If list of dicts: [ {'id': ...} ]
            # 2. If single dict: {'id': ...}
            # 3. If list of RPC responses: [{'result': [{'id': ...}], ...}] (Unlikely for create method in SDK?)
            
            result_item = None
            if isinstance(fact_results, list):
                if len(fact_results) > 0:
                   result_item = fact_results[0]
            elif isinstance(fact_results, dict):
                result_item = fact_results
            
            if not result_item:
                 raise ValueError(f"Could not parse create result: {fact_results}")

            if 'id' in result_item:
                fact_id = result_item['id']
            elif 'result' in result_item: # Check deep RPC format
                 # Sometimes create returns [{'result': [{'id': '...'}]}] ? No, SDK usually unwraps.
                 # But let's check.
                 pass
            else:
                 # Fallback, maybe it's just the ID? No.
                 pass
                 
            # If we still don't have fact_id, try to print and fail
            if 'id' not in result_item:
                 logger.error(f"DEBUG: result_item keys: {result_item.keys()}")
                 # Maybe it's buried deeper?
                 # Based on logs: val={'channel': 'character', ..., 'id': RecordID(...)}
                 # So it IS a dict with 'id'.
                 # Wait, previous error: "string indices must be integers" implies we tried to access a string?
                 # Ah, maybe `fact_results` WAS a list, but empty? No.
                 # Maybe `fact_results` WAS a string? Unlikely.
                 pass

            fact_id = result_item['id']

            # 2. Ensure Character and User exist (idempotent usually)
            # In SurrealDB, we can just refer to them by ID like `character:lillian`
            char_node = f"character:{agent_id}"
            user_node = f"user:{user_id}"
            
            # We can optionally 'create' them to set initial props, but linking works even if they are just IDs
            
            # 3. Create Edges
            # Character -> Observes -> Fact
            # We can store 'weight' on the edge based on importance
            await self.db.query(f"RELATE {char_node}->observes->{fact_id} SET weight = $weight, emotion = $emotion;", 
                                {"weight": importance / 10.0, "emotion": emotion})
            
            # Fact -> About -> User
            await self.db.query(f"RELATE {fact_id}->about->{user_node};")

            logger.info(f"💾 Memory stored: {fact_id}")
            return fact_id

        except Exception as e:
            logger.error(f"❌ Error adding memory: {e}")
            raise

    async def search(self, 
                    query_vector: List[float], 
                    agent_id: str, 
                    limit: int = 10, 
                    threshold: float = 0.6) -> List[Dict]:
        """
        Hybrid Search:
        Find facts that are:
        1. Observable by the agent (linked via `observes` edge) OR Public
        2. Semantically similar to query_vector
        """
        if not self.db:
            await self.connect()

        try:
            # SurrealQL query for personalized vector search
            # We filter by the agent's observation path
            
            # Strategy:
            # Select from 'fact' where:
            # 1. Connected to character via 'observes'
            # 2. Vector score is high
            
            # Note: direct filtering on relationships in WHERE clause with vector search might be tricky in one go.
            # Efficient pattern: Vector Search -> Filter by Graph
            
            query = """
            SELECT 
                text, 
                embedding, 
                importance,
                emotion,
                created_at,
                vector::similarity::cosine(embedding, $query_vec) AS score
            FROM fact
            WHERE vector::similarity::cosine(embedding, $query_vec) > $threshold
            AND (count(<-observes<-character) = 0 OR <-observes<-character = $agent_id)
            ORDER BY score DESC 
            LIMIT $limit;
            """
            
            # Wait, the graph filtering logic above:
            # `<-observes<-character` checks incoming edges from characters.
            # If `count(...) = 0`, it might mean it's orphaned? No.
            # We want: facts that THIS character observes.
            
            # Better Query Strategy for Isolation:
            # Start from Character -> traverse to Facts -> Filter by Vector
            
            query_graph = """
            SELECT 
                ->observes->fact.text AS text,
                ->observes->fact.importance AS importance,
                ->observes->fact.emotion AS emotion,
                ->observes->fact.created_at AS created_at,
                vector::similarity::cosine(->observes->fact.embedding, $query_vec) AS score
            FROM $agent_id
            ORDER BY score DESC
            LIMIT $limit;
            """
            
            # However, vector indexing optimization usually requires `FROM fact` to use HNSW efficiently.
            # Traversing from Character `->observes->fact` and calculating similarity on ALL memories might be slow if memory is huge.
            # BUT efficient for "Character's Memory" because the subset is smaller than "Global Memory".
            # For 10k-100k memories, standard traversal + calc is fast.
            # For HNSW usage, we should query `FROM fact` and constraint it.
            
            # Let's stick to the robust HNSW-first approach:
            # SELECT from fact WHERE ... AND <graph_condition>
            
            # For now, let's use the graph traversal approach (Query Graph) which guarantees isolation.
            # Optimization can be added later (e.g., pre-filtering).
            
            # Need to fix variable usage for table ID: "character:lillian"
            
            # Let's try the HNSW approach with graph filter:
            # "Select facts where cosine sim is high AND (linked to this character OR global)"
            
            query_optimized = """
            SELECT 
                id, 
                text, 
                importance, 
                created_at, 
                vector::similarity::cosine(embedding, $query_vec) AS score 
            FROM fact 
            WHERE 
                (<-observes<-character CONTAINS $agent_node OR count(<-observes<-character) = 0)
            ORDER BY score DESC 
            LIMIT $limit;
            """
            
            vars = {
                "query_vec": query_vector,
                "agent_node": f"character:{agent_id}",
                "limit": limit,
                #"threshold": threshold # Handled in code or query? Standard HNSW doesn't always support strict threshold in WHERE clause easily with index usage, but sorting works.
            }
            
            results = await self.db.query(query_optimized, vars)
            logger.info(f"DEBUG: search results type={type(results)} val={results}")
            
            # Results structure is usually [ {result: [...], status: 'OK', ...} ]
            # We need to parse it.
            
            if not results:
                return []
                
            # Check if it's a list of RPC responses
            if isinstance(results, list) and isinstance(results[0], dict) and 'status' in results[0]:
                 if results[0]['status'] != 'OK':
                    logger.warning(f"Search returned error status: {results[0]}")
                    return []
                 return results[0]['result']
            
            # Fallback (maybe direct list?)
            return results

        except Exception as e:
            logger.error(f"❌ Search error: {e}")
            return []

    async def close(self):
        if self.db:
            await self.db.close()
