import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from core.security.audit import AuditLogger


class StoreStub:
    def __init__(self):
        self.write_audit_event = AsyncMock()


@pytest.mark.anyio
async def test_audit_logger_uses_local_state_store_contract():
    store = StoreStub()
    with patch("services.infra.local_state_store.get_local_state_store", return_value=store):
        await AuditLogger.log_event(
            actor_id="module.test",
            action="permission_request",
            target="filesystem.read_assets",
        )

    store.write_audit_event.assert_awaited_once_with(
        actor_id="module.test",
        action="permission_request",
        target="filesystem.read_assets",
        status="granted",
        metadata=None,
    )


@pytest.mark.anyio
async def test_audit_logger_reliable_write_propagates_failure():
    store = StoreStub()
    store.write_audit_event = AsyncMock(side_effect=RuntimeError("audit db failed"))

    with patch("services.infra.local_state_store.get_local_state_store", return_value=store):
        with pytest.raises(RuntimeError, match="audit db failed"):
            await AuditLogger.log_event(
                actor_id="module.test",
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
            actor_id="module.test",
            action="permission_request",
            target="filesystem.read_assets",
        )
        import asyncio
        await asyncio.sleep(0)

    log_event.assert_awaited_once()
