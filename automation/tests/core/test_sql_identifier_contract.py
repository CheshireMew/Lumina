import pytest

from core.db.query_builder import SecurityException
from provider_drivers.memory_postgres.drivers.memory.query_builder import (
    PostgresQueryBuilder,
)
from provider_drivers.memory_sqlite.drivers.memory.query_builder import (
    SQLiteQueryBuilder,
)


@pytest.mark.parametrize("builder", [SQLiteQueryBuilder(), PostgresQueryBuilder()])
def test_memory_query_builders_reject_the_same_invalid_identifiers(builder):
    with pytest.raises(SecurityException):
        builder.sanitize_table("1invalid")
    with pytest.raises(SecurityException):
        builder.create("memory_items", {"bad-name": "value"})


@pytest.mark.parametrize("builder", [SQLiteQueryBuilder(), PostgresQueryBuilder()])
def test_memory_query_builders_share_order_by_fallback(builder):
    query, _params = builder.select("memory_items", order_by="created_at; DROP TABLE")
    assert "ORDER BY created_at DESC" in query
