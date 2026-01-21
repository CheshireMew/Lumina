import unittest
import sys
from pathlib import Path

# Add python_backend to path
PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.db.query_builder import SurrealQueryBuilder, SecurityException

class TestSurrealQueryBuilder(unittest.TestCase):
    def setUp(self):
        self.qb = SurrealQueryBuilder()

    def test_sanitize_table(self):
        self.assertEqual(self.qb.sanitize_table("users"), "users")
        self.assertEqual(self.qb.sanitize_table("user_profiles"), "user_profiles")
        
        with self.assertRaises(SecurityException):
            self.qb.sanitize_table("users; DROP TABLE users")
            
        with self.assertRaises(SecurityException):
            self.qb.sanitize_table("users--")

    def test_select_basic(self):
        query, params = self.qb.select("users")
        self.assertIn("SELECT * FROM users", query)
        self.assertIn("LIMIT $limit", query)
        self.assertEqual(params["limit"], 50)

    def test_select_with_where(self):
        where = {"name": "alice", "age": 30}
        query, params = self.qb.select("users", where=where)
        
        self.assertIn("name = $p_0", query)
        self.assertIn("age = $p_1", query)
        self.assertEqual(params["p_0"], "alice")
        self.assertEqual(params["p_1"], 30)

    def test_select_injection_attempt_in_key(self):
        # Keys (columns) are strictly sanitized
        where = {"name; DROP": "bad"}
        with self.assertRaises(SecurityException):
            self.qb.select("users", where=where)

    def test_delete(self):
        # Standard ID
        query, params = self.qb.delete("users", "user:123")
        self.assertIn("DELETE type::thing($tb, $id)", query)
        self.assertEqual(params["tb"], "users")
        self.assertEqual(params["id"], "123")
        
        # Simple ID (auto-handling)
        query, params = self.qb.delete("users", "123")
        self.assertEqual(params["id"], "123")

if __name__ == "__main__":
    unittest.main()
