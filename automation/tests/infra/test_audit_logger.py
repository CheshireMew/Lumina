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
        self.pool = PoolStub()

    async def get_pool(self):
        return self.pool


@pytest.mark.anyio
async def test_audit_logger_uses_lifecycle_bus_pool_contract():
    bus = BusStub()
    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=bus):
        await AuditLogger.log_event(
            actor_id="plugin.test",
            action="permission_request",
            target="filesystem.read_assets",
        )

    bus.pool.execute.assert_awaited_once()


@pytest.mark.anyio
async def test_audit_logger_reliable_write_propagates_failure():
    bus = BusStub()
    bus.pool.execute = AsyncMock(side_effect=RuntimeError("audit db failed"))

    with patch("services.infra.bus_factory.get_lifecycle_bus", return_value=bus):
        with pytest.raises(RuntimeError, match="audit db failed"):
            await AuditLogger.log_event(
                actor_id="plugin.test",
                action="permission_request",
                target="filesystem.read_assets",
            )


@pytest.mark.anyio
async def test_audit_logger_schedule_event_is_best_effort():
    with patch.object(
        AuditLogger,
        "log_event",
        AsyncMock(side_effect=RuntimeError("audit db failed")),
    ) as log_event:
        AuditLogger.schedule_event(
            actor_id="plugin.test",
            action="permission_request",
            target="filesystem.read_assets",
        )
        import asyncio
        await asyncio.sleep(0)

    log_event.assert_awaited_once()
