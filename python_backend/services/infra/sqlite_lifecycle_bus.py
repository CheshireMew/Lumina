import json
from typing import Any, Dict, List, Optional

from core.interfaces.lifecycle_bus import AbstractLifecycleBus
from core.schemas import WorkerState
from services.infra.local_state_store import LocalStateStore, get_local_state_store


class SQLiteLifecycleBus(AbstractLifecycleBus):
    """Process-safe local lifecycle state for the Windows desktop runtime."""

    def __init__(self, store: LocalStateStore | None = None):
        self._store = store or get_local_state_store()

    @property
    def is_connected(self) -> bool:
        return self._store.is_connected

    async def connect(self):
        await self._store.connect()

    async def disconnect(self):
        await self._store.close()

    async def update_worker_state(self, state: WorkerState):
        await self.send_heartbeat(
            state.worker_id,
            data=json.loads(state.model_dump_json()),
        )

    async def send_heartbeat(self, worker_id: str, data: Optional[Dict] = None):
        await self._store.send_heartbeat(worker_id, data)

    async def get_active_workers(self, timeout_seconds: int = 15) -> List[Dict[str, Any]]:
        return await self._store.get_active_workers(timeout_seconds)
