import json
import sys
from pathlib import Path
from types import SimpleNamespace

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


class FakePool:
    def __init__(self, conn):
        self.conn = conn
        self.closed = False

    def acquire(self):
        return AcquireContext(self.conn)

    async def close(self):
        self.closed = True


@pytest.mark.anyio
async def test_lifecycle_bus_connect_failure_propagates(monkeypatch):
    import services.infra.postgres_lifecycle_bus as bus_module

    async def fail_create_pool(**_kwargs):
        raise RuntimeError("postgres unavailable")

    monkeypatch.setattr(
        bus_module,
        "_load_asyncpg",
        lambda: SimpleNamespace(create_pool=fail_create_pool),
    )

    bus = bus_module.PostgresLifecycleBus()
    with pytest.raises(RuntimeError, match="postgres unavailable"):
        await bus.connect()

    assert not bus.is_connected
    assert bus._pool is None
    assert bus._listener_conn is None


@pytest.mark.anyio
async def test_lifecycle_bus_send_heartbeat_writes_worker_row():
    from services.infra.postgres_lifecycle_bus import PostgresLifecycleBus

    class Conn:
        def __init__(self):
            self.executed = []

        async def execute(self, sql, *args):
            self.executed.append((sql, args))

    conn = Conn()
    bus = PostgresLifecycleBus()
    bus._pool = FakePool(conn)
    bus._is_connected = True

    await bus.send_heartbeat("worker:stt", {"status": "healthy"})

    assert any("INSERT INTO worker_heartbeats" in sql for sql, _ in conn.executed)
    _, args = conn.executed[0]
    assert args[0] == "worker:worker_stt"
    assert args[1] == "worker:stt"
    assert json.loads(args[2]) == {"status": "healthy"}


@pytest.mark.anyio
async def test_lifecycle_bus_get_active_workers_fetches_recent_rows():
    from services.infra.postgres_lifecycle_bus import PostgresLifecycleBus

    class Conn:
        async def fetch(self, sql, timeout):
            assert "FROM worker_heartbeats" in sql
            assert timeout == 15
            return [{"worker_id": "worker:stt"}]

    bus = PostgresLifecycleBus()
    bus._pool = FakePool(Conn())
    bus._is_connected = True

    assert await bus.get_active_workers() == [{"worker_id": "worker:stt"}]
