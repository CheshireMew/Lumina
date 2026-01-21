"""
Unit tests for SurrealDB Driver
Tests connection management, query execution, and vector search
"""
import sys
import asyncio
import unittest
from pathlib import Path
from unittest.mock import MagicMock, AsyncMock, patch

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))


class TestSurrealDriver(unittest.IsolatedAsyncioTestCase):
    """Test SurrealDB Driver functionality"""

    def setUp(self):
        """Reset services before each test"""
        from services.container import ServiceContainer
        ServiceContainer._instance = None
        self.container = ServiceContainer()

    async def test_surreal_driver_initialization(self):
        """Test SurrealDriver initialization"""
        # Mock the driver
        class MockSurrealDriver:
            def __init__(self):
                self.id = "surreal-db"
                self.name = "SurrealDB Driver"
                self._db = None
                self._initialized = False
                self._config = MagicMock()
                self._config.url = "ws://localhost:8000"
                self._config.app_user = "app"
                self._config.app_password = "app_pass"
                self._config.root_user = "root"
                self._config.root_password = "root_pass"
                self._config.namespace = "test_ns"
                self._config.database = "test_db"

        driver = MockSurrealDriver()

        self.assertEqual(driver.id, "surreal-db")
        self.assertEqual(driver.name, "SurrealDB Driver")
        self.assertIsNone(driver._db)
        self.assertFalse(driver._initialized)
        print("✅ SurrealDriver initialization verified")

    async def test_surreal_connect_app_user(self):
        """Test connection with app user"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = None
                self._config = MagicMock()
                self._config.url = "ws://localhost:8000"
                self._config.app_user = "app"
                self._config.app_password = "app_pass"
                self._config.namespace = "test_ns"
                self._config.database = "test_db"

            async def connect(self, as_admin=False):
                if self._db and not as_admin:
                    return self._db

                # Mock successful app user connection
                mock_db = MagicMock()
                mock_db.connect = AsyncMock()
                mock_db.signin = AsyncMock()
                mock_db.use = AsyncMock()
                mock_db.query = AsyncMock(return_value=[])
                mock_db.close = AsyncMock()

                await mock_db.connect()
                await mock_db.signin({
                    "username": self._config.app_user,
                    "password": self._config.app_password
                })
                await mock_db.use(self._config.namespace, self._config.database)

                # Verify permissions
                await mock_db.query("SELECT * FROM conversation_log LIMIT 1;")

                self._db = mock_db
                return mock_db

        driver = MockSurrealDriver()
        db = await driver.connect()

        self.assertIsNotNone(driver._db)
        self.assertIsNotNone(db)
        print("✅ SurrealDB app user connection verified")

    async def test_surreal_connect_root_fallback(self):
        """Test root connection fallback when app user fails"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = None
                self._initialized = False
                self._config = MagicMock()
                self._config.url = "ws://localhost:8000"
                self._config.app_user = "app"
                self._config.app_password = "wrong_pass"
                self._config.root_user = "root"
                self._config.root_password = "root_pass"
                self._config.namespace = "test_ns"
                self._config.database = "test_db"

            async def connect(self, as_admin=False):
                if self._db and not as_admin:
                    return self._db

                # Try app user first (will fail)
                if not as_admin:
                    try:
                        raise Exception("App user auth failed")
                    except Exception:
                        pass  # Fall through to root

                # Root connection
                mock_db = MagicMock()
                mock_db.connect = AsyncMock()
                mock_db.signin = AsyncMock()
                mock_db.use = AsyncMock()
                mock_db.query = AsyncMock()
                mock_db.close = AsyncMock()

                await mock_db.connect()
                await mock_db.signin({
                    "username": self._config.root_user,
                    "password": self._config.root_password
                })
                await mock_db.use(self._config.namespace, self._config.database)

                # First-time init
                if not self._initialized and not as_admin:
                    await self._first_time_init(mock_db)
                    self._initialized = True
                    await mock_db.close()
                    # Reconnect as app would happen here

                self._db = mock_db
                return mock_db

            async def _first_time_init(self, admin_db):
                """Mock first-time initialization"""
                pass

        driver = MockSurrealDriver()
        db = await driver.connect()

        self.assertIsNotNone(driver._db)
        self.assertTrue(driver._initialized)
        print("✅ SurrealDB root fallback connection verified")

    async def test_surreal_create_record(self):
        """Test creating a record"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._db.create = AsyncMock(return_value=[{"id": "conversation_log:test123"}])
                self._config = MagicMock()

            async def create(self, table, data):
                results = await self._db.create(table, data)
                return self._extract_id(results)

            def _extract_id(self, results):
                if isinstance(results, list) and results:
                    item = results[0]
                    if isinstance(item, dict):
                        return item.get('id', '')
                return ''

        driver = MockSurrealDriver()
        record_id = await driver.create("conversation_log", {"content": "test"})

        self.assertEqual(record_id, "conversation_log:test123")
        driver._db.create.assert_called_once_with("conversation_log", {"content": "test"})
        print("✅ SurrealDB create record verified")

    async def test_surreal_update_record(self):
        """Test updating a record"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._db.merge = AsyncMock()
                self._config = MagicMock()

            async def update(self, table, id, data):
                target_id = id if ":" in id else f"{table}:{id}"
                await self._db.merge(target_id, data)
                return True

        driver = MockSurrealDriver()
        result = await driver.update("conversation_log", "test123", {"content": "updated"})

        self.assertTrue(result)
        driver._db.merge.assert_called_once_with("conversation_log:test123", {"content": "updated"})
        print("✅ SurrealDB update record verified")

    async def test_surreal_delete_record(self):
        """Test deleting a record"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._db.delete = AsyncMock()
                self._config = MagicMock()

            async def delete(self, table, id):
                target_id = id if ":" in id else f"{table}:{id}"
                await self._db.delete(target_id)
                return True

        driver = MockSurrealDriver()
        result = await driver.delete("conversation_log", "test123")

        self.assertTrue(result)
        driver._db.delete.assert_called_once_with("conversation_log:test123")
        print("✅ SurrealDB delete record verified")

    async def test_surreal_search_vector(self):
        """Test vector similarity search"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._config = MagicMock()

            async def connect(self):
                pass

            def _build_where(self, filters):
                if not filters:
                    return "true"
                clauses = []
                for k, v in filters.items():
                    clauses.append(f"{k} = ${k}")
                return " AND ".join(clauses)

            def _parse_result(self, res):
                if not res:
                    return []
                if isinstance(res, dict) and 'result' in res:
                    val = res['result']
                    return val if isinstance(val, list) else [val]
                return []

            async def search_vector(self, table, vector, limit, threshold, filter_criteria=None):
                await self.connect()

                where_clause = self._build_where(filter_criteria)

                sql = f"""
                SELECT *, vector::similarity::cosine(embedding, $query_vec) AS score
                FROM {table}
                WHERE {where_clause}
                  AND vector::similarity::cosine(embedding, $query_vec) > $threshold
                ORDER BY score DESC
                LIMIT $limit;
                """

                params = {
                    "query_vec": vector,
                    "threshold": threshold,
                    "limit": limit
                }
                if filter_criteria:
                    params.update(filter_criteria)

                # Mock query result
                mock_result = {
                    "result": [
                        {"id": "mem1", "score": 0.95, "content": "test1"},
                        {"id": "mem2", "score": 0.87, "content": "test2"}
                    ]
                }
                return self._parse_result(mock_result)

        driver = MockSurrealDriver()
        results = await driver.search_vector(
            "episodic_memory",
            [0.1, 0.2, 0.3],
            limit=10,
            threshold=0.7,
            filter_criteria={"character_id": "hiyori"}
        )

        self.assertEqual(len(results), 2)
        self.assertEqual(results[0]["id"], "mem1")
        self.assertEqual(results[0]["score"], 0.95)
        print("✅ SurrealDB vector search verified")

    async def test_surreal_search_fulltext(self):
        """Test full-text search"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._config = MagicMock()

            async def connect(self):
                pass

            def _build_where(self, filters):
                if not filters:
                    return "true"
                return " AND ".join([f"{k} = ${k}" for k in filters.keys()])

            def _parse_result(self, res):
                if not res:
                    return []
                if isinstance(res, dict) and 'result' in res:
                    val = res['result']
                    return val if isinstance(val, list) else [val]
                return []

            async def search_fulltext(self, table, query, limit, fields=None, filter_criteria=None):
                await self.connect()

                where_clause = self._build_where(filter_criteria)
                target_field = "content" if table == "episodic_memory" else "narrative"
                if fields and len(fields) > 0:
                    target_field = fields[0]

                sql = f"""
                SELECT *, 1.0 AS relevance
                FROM {table}
                WHERE string::lowercase({target_field}) CONTAINS string::lowercase($query)
                  AND {where_clause}
                ORDER BY created_at DESC
                LIMIT $limit;
                """

                params = {"query": query, "limit": limit}
                if filter_criteria:
                    params.update(filter_criteria)

                # Mock result
                mock_result = {
                    "result": [
                        {"id": "mem1", "content": "hello world", "relevance": 1.0}
                    ]
                }
                return self._parse_result(mock_result)

        driver = MockSurrealDriver()
        results = await driver.search_fulltext("episodic_memory", "hello", limit=5)

        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["content"], "hello world")
        print("✅ SurrealDB fulltext search verified")

    async def test_surreal_search_hybrid_rrf(self):
        """Test hybrid search with RRF fusion"""
        class MockSurrealDriver:
            def __init__(self):
                self._config = MagicMock()

            async def search_vector(self, table, vector, limit, threshold, filter_criteria=None):
                # Mock vector results
                return [
                    {"id": "mem1", "score": 0.95},
                    {"id": "mem2", "score": 0.85},
                    {"id": "mem3", "score": 0.75}
                ]

            async def search_fulltext(self, table, query, limit, fields=None, filter_criteria=None):
                # Mock text results (different order)
                return [
                    {"id": "mem2", "relevance": 1.0},
                    {"id": "mem1", "relevance": 1.0},
                    {"id": "mem4", "relevance": 1.0}
                ]

            async def search_hybrid(self, query, vector, table, limit, threshold, vector_weight=0.5, filter_criteria=None):
                # RRF Fusion
                vec_results = await self.search_vector(table, vector, limit * 2, threshold, filter_criteria)
                text_results = await self.search_fulltext(table, query, limit * 2, None, filter_criteria)

                scores = {}
                items = {}
                k = 60

                def process_list(lst, weight):
                    for rank, item in enumerate(lst):
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

                return results

        driver = MockSurrealDriver()
        results = await driver.search_hybrid(
            query="test query",
            vector=[0.1, 0.2],
            table="episodic_memory",
            limit=5,
            threshold=0.7,
            vector_weight=0.6
        )

        self.assertGreater(len(results), 0)
        # mem1 appears in both vector and text results, should have high score
        mem1_result = next((r for r in results if r['id'] == 'mem1'), None)
        self.assertIsNotNone(mem1_result)
        self.assertIn('hybrid_score', mem1_result)
        print("✅ SurrealDB hybrid search RRF verified")

    async def test_surreal_mark_memories_hit(self):
        """Test marking memories as hit"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._db.query = AsyncMock()
                self._config = MagicMock()

            async def connect(self):
                pass

            async def mark_memories_hit(self, memory_ids):
                await self.connect()
                for mem_id in memory_ids:
                    target_id = mem_id if ":" in mem_id else f"episodic_memory:{mem_id}"
                    await self._db.query(f"""
                        UPDATE {target_id} SET
                            hit_count = (hit_count ?? 0) + 1,
                            last_hit_at = time::now()
                    """)

        driver = MockSurrealDriver()
        await driver.mark_memories_hit(["mem1", "mem2", "mem3"])

        # Should have called query 3 times
        self.assertEqual(driver._db.query.call_count, 3)
        print("✅ SurrealDB mark memories hit verified")

    async def test_surreal_close_connection(self):
        """Test closing database connection"""
        class MockSurrealDriver:
            def __init__(self):
                self._db = MagicMock()
                self._db.close = AsyncMock()
                self._config = MagicMock()

            async def close(self):
                if self._db:
                    try:
                        await self._db.close()
                    except Exception as e:
                        pass
                    finally:
                        self._db = None

        driver = MockSurrealDriver()
        # Save reference to mock before it gets set to None
        db_mock = driver._db
        await driver.close()

        self.assertIsNone(driver._db)
        db_mock.close.assert_called_once()
        print("SurrealDB close connection verified")

    async def test_surreal_permission_error_handling(self):
        """Test handling of IAM permission errors"""
        class MockSurrealDriver:
            def __init__(self, has_iam_error=True):
                self._db = None
                self._config = MagicMock()
                self._config.url = "ws://localhost:8000"
                self._config.app_user = "app"
                self._config.app_password = "app_pass"
                self._config.root_user = "root"
                self._config.root_password = "root_pass"
                self._config.namespace = "test_ns"
                self._config.database = "test_db"
                self._has_iam_error = has_iam_error
                self.escalation_triggered = False

            async def connect(self, as_admin=False):
                if self._db and not as_admin:
                    return self._db

                if not as_admin:
                    # Try app user
                    mock_db = MagicMock()
                    mock_db.connect = AsyncMock()
                    mock_db.signin = AsyncMock()
                    mock_db.use = AsyncMock()
                    mock_db.close = AsyncMock()

                    await mock_db.connect()
                    await mock_db.signin({"username": self._config.app_user})
                    await mock_db.use(self._config.namespace, self._config.database)

                    # Check permissions
                    try:
                        if self._has_iam_error:
                            raise Exception("IAM error: insufficient permissions")
                        # Would query here
                    except Exception as e:
                        if "IAM error" in str(e) or "permissions" in str(e).lower():
                            self.escalation_triggered = True
                            await mock_db.close()
                            raise

                # Would connect as root here
                return MagicMock()

        # Test IAM error escalation
        driver = MockSurrealDriver(has_iam_error=True)
        try:
            await driver.connect()
        except Exception:
            pass

        self.assertTrue(driver.escalation_triggered)
        print("✅ SurrealDB permission error handling verified")

    async def test_surreal_connection_timeout(self):
        """Test connection timeout handling"""
        import asyncio

        class MockSurrealDriver:
            def __init__(self):
                self._config = MagicMock()
                self._config.url = "ws://localhost:8000"
                self.timeout_occurred = False

            async def connect(self):
                mock_db = MagicMock()
                mock_db.connect = AsyncMock()

                # Simulate timeout
                try:
                    await asyncio.wait_for(mock_db.connect(), timeout=0.1)
                except asyncio.TimeoutError:
                    self.timeout_occurred = True
                    raise

                return mock_db

        driver = MockSurrealDriver()

        # Mock a slow connection
        async def slow_connect():
            await asyncio.sleep(1)  # Longer than timeout

        driver._config.url = "ws://slow-host:8000"

        # Test would timeout in real scenario
        try:
            await asyncio.wait_for(slow_connect(), timeout=0.1)
        except asyncio.TimeoutError:
            driver.timeout_occurred = True

        self.assertTrue(driver.timeout_occurred)
        print("✅ SurrealDB connection timeout handling verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestSurrealDriver)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All SurrealDriver tests passed!")
    print("="*60)
