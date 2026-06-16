import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.security.audit import AuditLogger


class PoolStub:
    def __init__(self):
        self.execute = AsyncMock()


class BusStub:
    def __init__(self):
        self.is_connected = False
        self.connect = AsyncMock(side_effect=self._connect)
        self.pool = PoolStub()

    async def _connect(self):
        self.is_connected = True

    async def get_pool(self):
        return self.pool


@pytest.mark.anyio
async def test_audit_logger_uses_lifecycle_bus_connection_contract():
    bus = BusStub()
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=bus):
        await AuditLogger.log_event(
            actor_id="plugin.test",
            action="permission_request",
            target="filesystem.read_assets",
        )

    bus.connect.assert_awaited_once_with()
    bus.pool.execute.assert_awaited_once()
