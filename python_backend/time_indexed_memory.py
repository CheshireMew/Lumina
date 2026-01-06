
import sqlite3
import json
import uuid
import os
from datetime import datetime
from typing import List, Dict, Optional, Any

class TimeIndexedMemory:
    def __init__(self, db_path: str):
        """
        Initialize the SQLite Time-Indexed Memory.
        
        Args:
            db_path: Path to the SQLite database file.
        """
        self.db_path = db_path
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        """Get a database connection with Row factory enabled."""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        """Initialize database schema, indexes, and FTS5 virtual table."""
        dirname = os.path.dirname(self.db_path)
        if dirname:
            os.makedirs(dirname, exist_ok=True)
        
        with self._get_connection() as conn:
            # Enable Write-Ahead Logging for better concurrency
            conn.execute("PRAGMA journal_mode=WAL;")
            
            # --- 1. Main Table ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memories (
                id TEXT PRIMARY KEY,
                character_id TEXT NOT NULL,
                type TEXT NOT NULL,         -- 'dialogue', 'fact', 'summary'
                content TEXT NOT NULL,
                created_at DATETIME NOT NULL,
                importance INTEGER DEFAULT 1, -- 1-10
                emotion TEXT DEFAULT 'neutral',
                source_id TEXT,             -- Lineage: ID of the source interaction
                metadata JSON DEFAULT '{}',
                is_deleted BOOLEAN DEFAULT 0
            );
            """)
            
            # --- 2. Indexes ---
            conn.execute("CREATE INDEX IF NOT EXISTS idx_time ON memories(created_at);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_char ON memories(character_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_type ON memories(type);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_source ON memories(source_id);")
            
            # --- 3. FTS5 Virtual Table (External Content Mode) ---
            # content='memories' means we don't duplicate text storage, we point to the main table.
            # content_rowid='rowid' maps the FTS docid to the main table's internal rowid.
            conn.execute("""
            CREATE VIRTUAL TABLE IF NOT EXISTS memories_fts 
            USING fts5(content, content='memories', content_rowid='rowid');
            """)
            
            # --- 4. Triggers to keep FTS Synced ---
            
            # Trigger: After INSERT
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ai AFTER INSERT ON memories BEGIN
              INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
            END;
            """)
            
            # Trigger: After DELETE
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_ad AFTER DELETE ON memories BEGIN
              INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
            END;
            """)
            
            # Trigger: After UPDATE
            conn.execute("""
            CREATE TRIGGER IF NOT EXISTS memories_au AFTER UPDATE ON memories BEGIN
              INSERT INTO memories_fts(memories_fts, rowid, content) VALUES('delete', old.rowid, old.content);
              INSERT INTO memories_fts(rowid, content) VALUES (new.rowid, new.content);
            END;
            """)
            
            # --- 5. Event Store (Event Sourcing) ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_events (
                event_id TEXT PRIMARY KEY,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                event_type TEXT,        -- 'observation', 'interaction', 'reflection', 'archived_chat'
                content TEXT,           -- Raw textual content
                calc_embedding BOOLEAN DEFAULT 0,
                processed BOOLEAN DEFAULT 0
            );
            """)

            # Schema Migration: Ensure 'processed' column exists for existing DBs
            try:
                conn.execute("ALTER TABLE memory_events ADD COLUMN processed BOOLEAN DEFAULT 0")
            except Exception:
                pass # Column likely exists

            # --- 6. Graph Edges (Pseudo-Graph) ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS memory_edges (
                source_id TEXT,
                target_id TEXT,
                relation TEXT,          -- e.g. 'likes', 'visited', 'is_a'
                weight REAL DEFAULT 1.0,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (source_id, target_id, relation)
            );
            """)
            
            # Graph Indexes
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_source ON memory_edges (source_id);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_edge_target ON memory_edges (target_id);")

            # --- 7. Conversation Buffer (Three-Layer Architecture) ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS conversation_buffer (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_name TEXT NOT NULL,
                char_name TEXT NOT NULL,
                user_input TEXT NOT NULL,
                ai_response TEXT NOT NULL,
                timestamp DATETIME NOT NULL,
                processed INTEGER DEFAULT 0,
                batch_id TEXT
            );
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_processed ON conversation_buffer (processed);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_conv_timestamp ON conversation_buffer (timestamp);")

            # --- 8. Facts Staging (Dual-Channel Processing) ---
            conn.execute("""
            CREATE TABLE IF NOT EXISTS facts_staging (
                id TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                emotion TEXT DEFAULT 'neutral',
                importance INTEGER DEFAULT 1,
                timestamp DATETIME NOT NULL,
                channel TEXT NOT NULL,          -- 'user' or 'character'
                source_name TEXT NOT NULL,      -- Actual name (e.g., '柴郡', 'hiyori')
                vector_id TEXT NOT NULL,        -- Qdrant point ID
                consolidated INTEGER DEFAULT 0,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP
            );
            """)
            
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_channel ON facts_staging (channel);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_consolidated ON facts_staging (consolidated);")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_facts_timestamp ON facts_staging (timestamp);")

            conn.commit()
            print(f"[TimeIndexedMemory] Database initialized at: {self.db_path}")

    def add_event(self, content: str, event_type: str = "interaction") -> str:
        """Appends an event to the Event Store (Log)."""
        event_id = f"evt_{int(datetime.now().timestamp()*1000)}_{uuid.uuid4().hex[:4]}" # More unique ID
        with self._get_connection() as conn:
            conn.execute(
                "INSERT INTO memory_events (event_id, event_type, content, processed) VALUES (?, ?, ?, 0)",
                (event_id, event_type, content)
            )
            conn.commit()
        return event_id

    def fetch_unprocessed_events(self, limit: int = 50) -> List[Dict]:
        """Fetch raw events that haven't been processed by Dreaming Service yet."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT * FROM memory_events WHERE processed = 0 AND event_type IN ('interaction', 'archived_chat') ORDER BY timestamp ASC LIMIT ?",
                (limit,)
            )
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def mark_events_processed(self, event_ids: List[str]):
        """Mark events as processed after Dreaming analysis."""
        if not event_ids: return
        with self._get_connection() as conn:
            placeholders = ','.join('?' for _ in event_ids)
            conn.execute(
                f"UPDATE memory_events SET processed = 1 WHERE event_id IN ({placeholders})",
                event_ids
            )
            conn.commit()

    def add_graph_edge(self, source: str, target: str, relation: str, weight: float = 1.0):
        """Adds a directed edge to the Knowledge Graph."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO memory_edges (source_id, target_id, relation, weight)
                VALUES (?, ?, ?, ?)
            """, (source, target, relation, weight))
            conn.commit()

    def get_graph_context(self, memory_ids: List[str], hops: int = 1) -> List[Dict]:
        """
        Performs a 'Graph Expansion' (1-Hop) for the given seed memory IDs.
        Retrieves related nodes connected to the search results.
        """
        if not memory_ids:
            return []
            
        placeholders = ','.join(['?'] * len(memory_ids))
        results = []
        
        with self._get_connection() as conn:
            # Find all outgoing edges from these memories
            rows = conn.execute(f"""
                SELECT source_id, relation, target_id, weight 
                FROM memory_edges 
                WHERE source_id IN ({placeholders})
            """, memory_ids).fetchall()
            
            for r in rows:
                results.append({
                    "source": r[0],
                    "relation": r[1],
                    "target": r[2],
                    "weight": r[3]
                })
        return results

    def add_memory(self, 
                   character_id: str, 
                   content: str, 
                   type: str = "fact", 
                   created_at: Optional[str] = None,
                   importance: int = 1,
                   emotion: str = "neutral",
                   source_id: str = None,
                   metadata: Dict = None,
                   memory_id: Optional[str] = None) -> str:
        """
        Add a memory entry.
        
        Args:
            memory_id: Optional explicit UUID. If None, one is generated.
            ...
        Returns:
            The memory ID (UUID string).
        """
        if not created_at:
            created_at = datetime.now().isoformat()
        if not metadata:
            metadata = {}
            
        # Use provided ID (essential for Dual-Write sync with Qdrant) or generate new
        mem_id = memory_id if memory_id else str(uuid.uuid4())
        
        with self._get_connection() as conn:
            conn.execute("""
            INSERT INTO memories (
                id, character_id, type, content, created_at, 
                importance, emotion, source_id, metadata, is_deleted
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 0)
            """, (
                mem_id, 
                character_id, 
                type, 
                content, 
                created_at, 
                importance, 
                emotion, 
                source_id, 
                json.dumps(metadata, ensure_ascii=False)
            ))
            conn.commit()
            
        # print(f"[TimeIndexedMemory] Added {type}: {content[:30]}...")
        return mem_id

    def get_memories_by_time_range(self, 
                                 character_id: str, 
                                 start_time: str, 
                                 end_time: str,
                                 limit: int = 100) -> List[Dict]:
        """
        Retrieve memories within a specific time range.
        Format of start_time/end_time: ISO8601 string (e.g., '2026-01-01T00:00:00')
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
            SELECT * FROM memories 
            WHERE character_id = ? 
              AND created_at BETWEEN ? AND ?
              AND is_deleted = 0
            ORDER BY created_at ASC
            LIMIT ?
            """, (character_id, start_time, end_time, limit))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_memories_by_keyword(self, 
                              character_id: str, 
                              keyword_query: str, 
                              limit: int = 20) -> List[Dict]:
        """
        Full-Text Search using FTS5.
        
        Args:
            keyword_query: The search phrase (e.g. "API Key" or "Apple AND Banana")
        """
        with self._get_connection() as conn:
            # Join FTS table with Main table to get full details (and filter by char_id)
            # Note: We query the FTS table for matches, then join 'memories' on rowid
            
            # Simple sanitization for FTS syntax: escape double quotes
            safe_query = keyword_query.replace('"', '""')
            
            # We construct a query string safely. 
            # Note: FTS5 query syntax is powerful. We assume user passes simple text.
            # We wrap in quotes for phrase search? Or just pass through?
            # Let's wrap in quotes "..." to treat as phrase if it contains spaces?
            # For now, let's just pass raw string and rely on basic tokenization.
            
            query = f"""
            SELECT m.* 
            FROM memories m
            JOIN memories_fts f ON m.rowid = f.rowid
            WHERE memories_fts MATCH ?
              AND m.character_id = ?
              AND m.is_deleted = 0
            ORDER BY rank
            LIMIT ?
            """
            
            try:
                cursor = conn.execute(query, (safe_query, character_id, limit))
                rows = cursor.fetchall()
                return [dict(row) for row in rows]
            except sqlite3.OperationalError as e:
                print(f"[TimeIndexedMemory] FTS Search Error: {e}")
                return []

    def soft_delete_memory(self, memory_id: str):
        with self._get_connection() as conn:
            conn.execute("UPDATE memories SET is_deleted = 1 WHERE id = ?", (memory_id,))
            conn.commit()

    def hard_delete_memory(self, memory_id: str):
        """Actually remove row. FTS trigger will handle index update."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM memories WHERE id = ?", (memory_id,))
            conn.commit()

    def get_recent_memories(self, character_id: str, limit: int = 50, memory_type: str = None) -> List[Dict]:
        """Fetch most recent memories, optionally filtering by type (e.g. 'fact')."""
        with self._get_connection() as conn:
            query = "SELECT * FROM memories WHERE character_id = ? AND is_deleted = 0"
            params = [character_id]
            
            if memory_type:
                query += " AND type = ?"
                params.append(memory_type)
                
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            cursor = conn.execute(query, params)
            return [dict(row) for row in cursor.fetchall()]

    def get_recent_chat_history(self, limit: int = 50) -> List[Dict]:
        """Fetch recent raw interactions/chat events."""
        with self._get_connection() as conn:
            # We want raw events that are likely chat logs
            cursor = conn.execute("""
                SELECT * FROM memory_events 
                WHERE event_type IN ('user_interaction', 'archived_chat', 'chat')
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def view_knowledge_graph(self, limit: int = 100) -> Dict[str, Any]:
        """
        Dump the latest graph edges for visualization.
        Returns { "nodes": [], "edges": [] } compatible format.
        """
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT source_id, target_id, relation, weight
                FROM memory_edges
                ORDER BY timestamp DESC
                LIMIT ?
            """, (limit,))
            
            edges = []
            nodes_set = set()
            
            for row in cursor:
                src, tgt, rel, w = row
                edges.append({
                    "source": src,
                    "target": tgt,
                    "label": rel,
                    "weight": w
                })
                nodes_set.add(src)
                nodes_set.add(tgt)
            
            return {
                "nodes": [{"id": n} for n in nodes_set],
                "edges": edges
            }

    # ============================================
    # Three-Layer Architecture Helper Methods
    # ============================================
    
    def add_conversation(self, user_name: str, char_name: str, 
                        user_input: str, ai_response: str, timestamp: str):
        """Add a conversation to the buffer for batch processing."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO conversation_buffer 
                (user_name, char_name, user_input, ai_response, timestamp)
                VALUES (?, ?, ?, ?, ?)
            """, (user_name, char_name, user_input, ai_response, timestamp))
            conn.commit()
    
    def get_unprocessed_conversations(self, limit: int = 20) -> List[Dict]:
        """Fetch unprocessed conversations for FactExtractor batching."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM conversation_buffer 
                WHERE processed=0 
                ORDER BY timestamp ASC 
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_conversations_processed(self, conversation_ids: List[int], batch_id: str):
        """Mark conversations as processed after fact extraction."""
        with self._get_connection() as conn:
            placeholders = ','.join('?' * len(conversation_ids))
            conn.execute(f"""
                UPDATE conversation_buffer 
                SET processed=1, batch_id=? 
                WHERE id IN ({placeholders})
            """, [batch_id] + conversation_ids)
            conn.commit()
    
    def add_fact_staging(self, fact_id: str, text: str, emotion: str, 
                        importance: int, timestamp: str, channel: str, 
                        source_name: str, vector_id: str):
        """Add an extracted fact to the staging table."""
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO facts_staging 
                (id, text, emotion, importance, timestamp, channel, source_name, vector_id)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (fact_id, text, emotion, importance, timestamp, channel, source_name, vector_id))
            conn.commit()
    
    def get_unconsolidated_facts(self, channel: str, limit: int = 10) -> List[Dict]:
        """Fetch unconsolidated facts for a specific channel."""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM facts_staging 
                WHERE channel=? AND consolidated=0
                ORDER BY timestamp ASC
                LIMIT ?
            """, (channel, limit))
            return [dict(row) for row in cursor.fetchall()]
    
    def mark_facts_consolidated(self, fact_ids: List[str]):
        """Mark facts as consolidated after MemoryConsolidator processing."""
        with self._get_connection() as conn:
            placeholders = ','.join('?' * len(fact_ids))
            conn.execute(f"""
                UPDATE facts_staging 
                SET consolidated=1 
                WHERE id IN ({placeholders})
            """, fact_ids)
            conn.commit()
    
    def delete_fact_staging(self, fact_id: str):
        """Delete a fact from staging (used when LLM decides to remove duplicates)."""
        with self._get_connection() as conn:
            conn.execute("DELETE FROM facts_staging WHERE id=?", (fact_id,))
            conn.commit()
    
    def get_conversations_count(self, processed: bool = False) -> int:
        """Get count of processed/unprocessed conversations."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM conversation_buffer WHERE processed=?", 
                (1 if processed else 0,)
            )
            return cursor.fetchone()[0]
    
    def get_facts_count(self, channel: str, consolidated: bool = False) -> int:
        """Get count of consolidated/unconsolidated facts for a channel."""
        with self._get_connection() as conn:
            cursor = conn.execute(
                "SELECT COUNT(*) FROM facts_staging WHERE channel=? AND consolidated=?",
                (channel, 1 if consolidated else 0)
            )
            return cursor.fetchone()[0]
    
    def get_consolidated_facts(self, limit: int = 50, channel: Optional[str] = None) -> List[Dict]:
        """
        获取已巩固的 Facts（供 Memory Inspector UI 显示）
        
        Args:
            limit: 返回结果数量限制
            channel: 可选，筛选特定频道 ('user' 或 'character')
            
        Returns:
            Facts 列表，字段名与 memories 表兼容（content, created_at 等）
        """
        with self._get_connection() as conn:
            if channel:
                query = """
                    SELECT id, text as content, emotion, importance, 
                           timestamp as created_at, channel, source_name 
                    FROM facts_staging 
                    WHERE consolidated=1 AND channel=?
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                cursor = conn.execute(query, (channel, limit))
            else:
                query = """
                    SELECT id, text as content, emotion, importance, 
                           timestamp as created_at, channel, source_name 
                    FROM facts_staging 
                    WHERE consolidated=1 
                    ORDER BY timestamp DESC 
                    LIMIT ?
                """
                cursor = conn.execute(query, (limit,))
            
            return [dict(row) for row in cursor.fetchall()]

    def get_random_memories(self, character_id: str, limit: int = 3, type_filter: str = 'fact') -> List[Dict]:
        """Get random memories for inspiration, prioritizing facts."""
        with self._get_connection() as conn:
            # Try to get facts first
            query = """
            SELECT content, created_at, importance, emotion 
            FROM memories 
            WHERE character_id = ? AND type = ? AND is_deleted = 0
            ORDER BY RANDOM() 
            LIMIT ?
            """
            cursor = conn.execute(query, (character_id, type_filter, limit))
            rows = cursor.fetchall()
            results = [dict(row) for row in rows]
            
            # If not enough facts, try dialogues
            if len(results) < limit and type_filter == 'fact':
                 remaining = limit - len(results)
                 query2 = """
                 SELECT content, created_at, importance, emotion 
                 FROM memories 
                 WHERE character_id = ? AND type = 'dialogue' AND is_deleted = 0
                 ORDER BY RANDOM() 
                 LIMIT ?
                 """
                 cursor2 = conn.execute(query2, (character_id, remaining))
                 rows2 = cursor2.fetchall()
                 results.extend([dict(row) for row in rows2])
                 
            return results

# Test stub
if __name__ == "__main__":
    db_path = "test_memory.db"
    if os.path.exists(db_path):
        os.remove(db_path)
        
    tm = TimeIndexedMemory(db_path)
    
    # Test Add
    tm.add_memory("test_char", "I love apples", type="fact", importance=5)
    tm.add_memory("test_char", "I hate bugs", type="fact", importance=2)
    tm.add_memory("test_char", "The secret API key is 12345", type="fact", importance=10)
    
    # Test Time Search
    d1 = datetime.now().isoformat()
    # ...
    
    # Test FTS Search
    results = tm.get_memories_by_keyword("test_char", "API key")
    print("\nFTS Search Results for 'API key':")
    for r in results:
        print(f" - {r['content']} (Score: {r['importance']})")
        
    # Clean up
    if os.path.exists(db_path):
        try:
             os.remove(db_path) # Might fail if WAL is locked
        except:
             pass
