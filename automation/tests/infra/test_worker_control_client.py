import asyncio
from unittest.mock import AsyncMock

import pytest

from services.infra.worker_control_client import WorkerControlClient


@pytest.mark.anyio
async def test_stop_absorbs_task_failures_during_connection_teardown():
    client = WorkerControlClient(
        worker_id="worker:test",
        worker_type="test",
        main_port=8010,
        worker_port=8765,
    )
    client._running = True
    client._connected = True
    websocket = AsyncMock()
    client._ws = websocket

    async def fail_on_close():
        await asyncio.sleep(0)
        raise RuntimeError("connection closed while stopping")

    client._receive_task = asyncio.create_task(fail_on_close())
    await client.stop()

    websocket.close.assert_awaited_once()
    assert client._ws is None
    assert client._receive_task is None
    assert client.is_connected is False
