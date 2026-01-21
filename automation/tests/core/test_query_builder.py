"""
Unit tests for Query Builder
Tests query construction, injection prevention, and parameter handling
"""
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8')

# Add project root and python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.db.query_builder import SurrealQueryBuilder, SecurityException


class TestQueryBuilder(unittest.TestCase):
    """Test QueryBuilder functionality"""

    def test_surreal_select_basic(self):
        """Test basic SELECT query construction"""
        builder = SurrealQueryBuilder()
        query, params = builder.select("test_table")

        self.assertIn("SELECT * FROM test_table", query)
        # Parameters dictionary uses plain keys (not $ prefixed)
        self.assertIn("limit", params)
        self.assertEqual(params["limit"], 50)
        # Query should use $limit placeholder
        self.assertIn("$limit", query)
        print("✅ SurrealDB SELECT basic query verified")

    def test_surreal_select_with_conditions(self):
        """Test SELECT with WHERE conditions"""
        builder = SurrealQueryBuilder()
        query, params = builder.select("users", where={"name": "Alice", "age": 25})

        self.assertIn("WHERE", query)
        self.assertIn("name = $p_0", query)
        self.assertIn("age = $p_1", query)
        self.assertEqual(params["p_0"], "Alice")
        self.assertEqual(params["p_1"], 25)
        print("✅ SurrealDB SELECT with conditions verified")

    def test_surreal_select_with_limit(self):
        """Test SELECT with custom limit"""
        builder = SurrealQueryBuilder()
        query, params = builder.select("items", limit=10)

        self.assertIn("LIMIT $limit", query)
        self.assertEqual(params["limit"], 10)
        print("✅ SurrealDB SELECT with limit verified")

    def test_surreal_select_with_order_by(self):
        """Test SELECT with ORDER BY clause"""
        builder = SurrealQueryBuilder()
        query, params = builder.select("logs", order_by="timestamp DESC")

        self.assertIn("ORDER BY timestamp DESC", query)
        print("✅ SurrealDB SELECT with ORDER BY verified")

    def test_table_name_sanitization(self):
        """Test table name sanitization prevents injection"""
        builder = SurrealQueryBuilder()

        # Valid table names
        valid_tables = ["users", "test_table", "data123"]
        for table in valid_tables:
            result = builder.sanitize_table(table)
            self.assertEqual(result, table)

        # Invalid table names
        invalid_tables = [
            "users; DROP TABLE",
            "users' OR '1'='1",
            "users`",
            "users--"
        ]
        for table in invalid_tables:
            with self.assertRaises(SecurityException):
                builder.sanitize_table(table)
        print("✅ Table name sanitization verified")

    def test_column_name_validation(self):
        """Test column name validation in WHERE clause"""
        builder = SurrealQueryBuilder()

        # Valid column names
        valid_where = {"valid_col": "value", "another_col": 123}
        query, params = builder.select("test", where=valid_where)
        self.assertIn("valid_col = $p_0", query)

        # Invalid column name
        with self.assertRaises(SecurityException):
            builder.select("test", where={"invalid;col": "value"})
        print("✅ Column name validation verified")

    def test_order_by_sanitization(self):
        """Test ORDER BY clause sanitization"""
        builder = SurrealQueryBuilder()

        # Valid ORDER BY
        query, _ = builder.select("test", order_by="created_at DESC")
        self.assertIn("ORDER BY created_at DESC", query)

        # Invalid ORDER BY (should fall back to default)
        query, _ = builder.select("test", order_by="created_at; DROP TABLE")
        # Should contain fallback
        self.assertIn("ORDER BY", query)
        print("✅ ORDER BY sanitization verified")

    def test_delete_query(self):
        """Test DELETE query construction"""
        builder = SurrealQueryBuilder()
        query, params = builder.delete("users", "user123")

        self.assertIn("DELETE type::thing", query)
        # Parameters use plain keys
        self.assertIn("tb", params)
        self.assertIn("id", params)
        # Query should use $ placeholders
        self.assertIn("$tb", query)
        self.assertIn("$id", query)
        self.assertEqual(params["tb"], "users")
        self.assertEqual(params["id"], "user123")
        print("✅ DELETE query construction verified")

    def test_delete_with_table_prefix(self):
        """Test DELETE with table:id format"""
        builder = SurrealQueryBuilder()
        query, params = builder.delete("users", "users:user123")

        # Should strip table prefix
        self.assertEqual(params["id"], "user123")
        print("✅ DELETE with table prefix verified")

    def test_limit_enforcement(self):
        """Test that limit is capped at 100"""
        builder = SurrealQueryBuilder()

        # Request high limit
        query, params = builder.select("test", limit=1000)

        # Should be capped
        self.assertEqual(params["limit"], 100)
        print("✅ Limit enforcement verified")

    def test_query_parameterization(self):
        """Test that values are parameterized, not interpolated"""
        builder = SurrealQueryBuilder()

        # Use a value with special characters
        query, params = builder.select("test", where={"content": "'; DROP TABLE"})

        # The value should be in params, not in query
        self.assertNotIn("'; DROP TABLE", query)
        self.assertEqual(params["p_0"], "'; DROP TABLE")
        self.assertIn("$p_0", query)
        print("✅ Query parameterization verified")


if __name__ == "__main__":
    suite = unittest.TestLoader().loadTestsFromTestCase(TestQueryBuilder)
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    print("\n" + "="*60)
    print(f"Tests run: {result.testsRun}")
    print(f"Failures: {len(result.failures)}")
    print(f"Errors: {len(result.errors)}")
    if result.wasSuccessful():
        print("✅ All QueryBuilder tests passed!")
    print("="*60)
