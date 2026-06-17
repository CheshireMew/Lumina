import sys
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

PROJECT_ROOT = Path(__file__).parents[3]
sys.path.append(str(PROJECT_ROOT / "python_backend"))
sys.path.append(str(PROJECT_ROOT))

from services.reporting.worker_reporter import WorkerStatusReporter


class BusStub:
    def __init__(self):
        self.is_connected = False
        self.connect = AsyncMock(side_effect=self._connect)
        self.update_worker_state = AsyncMock()

    async def _connect(self):
        self.is_connected = True


@pytest.mark.anyio
async def test_force_report_uses_lifecycle_bus_connection_contract():
    bus = BusStub()
    with patch(
        "services.infra.bus_factory.get_lifecycle_bus",
        return_value=bus,
    ):
        reporter = WorkerStatusReporter(
            worker_id="worker:test",
            state_provider=lambda: [{"id": "plugin.test", "name": "Plugin Test"}],
            port=8001,
        )

    await reporter.force_report()

    bus.connect.assert_awaited_once_with()
    bus.update_worker_state.assert_awaited_once()
