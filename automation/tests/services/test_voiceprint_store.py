import sys
from pathlib import Path
from unittest.mock import patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))


class AcquireContext:
    def __init__(self, conn):
        self.conn = conn

    async def __aenter__(self):
        return self.conn

    async def __aexit__(self, exc_type, exc, tb):
        return False


class Conn:
    def __init__(self):
        self.executed = []
        self.rows = []

    async def execute(self, sql, *args):
        self.executed.append((sql, args))

    async def fetch(self, sql, *args):
        self.executed.append((sql, args))
        return self.rows


class PostgresOnlyPool:
    def __init__(self, conn):
        self.conn = conn

    def acquire(self):
        return AcquireContext(self.conn)

    async def select(self, *_args):
        raise AssertionError("legacy select API must not be used")

    async def query(self, *_args):
        raise AssertionError("legacy query API must not be used")

    async def delete(self, *_args):
        raise AssertionError("legacy delete API must not be used")


class Bus:
    def __init__(self, pool=None, error=None):
        self.pool = pool
        self.error = error

    async def get_pool(self):
        if self.error:
            raise self.error
        return self.pool


@pytest.mark.anyio
async def test_voiceprint_list_profiles_uses_postgres_pool_only():
    from services import voiceprint_store

    conn = Conn()
    conn.rows = [
        {
            "id": "voiceprint_profiles:alice",
            "name": "alice",
            "enabled": True,
            "embedding": "abc",
            "created_at": "created",
            "updated_at": "updated",
        }
    ]
    bus = Bus(PostgresOnlyPool(conn))

    with patch("services.voiceprint_store.get_lifecycle_bus", return_value=bus):
        profiles = await voiceprint_store.list_profiles()

    assert profiles == conn.rows
    assert any("CREATE TABLE IF NOT EXISTS voiceprint_profiles" in sql for sql, _ in conn.executed)
    assert any("SELECT id, name, enabled, embedding" in sql for sql, _ in conn.executed)


@pytest.mark.anyio
async def test_voiceprint_mutations_use_postgres_pool_only():
    from services import voiceprint_store

    conn = Conn()
    bus = Bus(PostgresOnlyPool(conn))

    with patch("services.voiceprint_store.get_lifecycle_bus", return_value=bus):
        await voiceprint_store.set_profile_enabled("alice", False)
        await voiceprint_store.delete_profile("alice")
        await voiceprint_store.upsert_profile("alice", "embedding", enabled=True)

    statements = [sql for sql, _ in conn.executed]
    assert any("UPDATE voiceprint_profiles" in sql for sql in statements)
    assert any("DELETE FROM voiceprint_profiles" in sql for sql in statements)
    assert any("INSERT INTO voiceprint_profiles" in sql for sql in statements)


@pytest.mark.anyio
async def test_voiceprint_pool_failure_raises_domain_error():
    from services import voiceprint_store

    bus = Bus(error=RuntimeError("postgres unavailable"))

    with patch("services.voiceprint_store.get_lifecycle_bus", return_value=bus):
        with pytest.raises(voiceprint_store.VoiceprintStoreUnavailable) as exc_info:
            await voiceprint_store.list_profiles()

    assert "Voiceprint database is unavailable" in str(exc_info.value)
    assert isinstance(exc_info.value.__cause__, RuntimeError)
