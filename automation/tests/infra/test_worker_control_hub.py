import sys
import types
from contextvars import ContextVar
from unittest.mock import MagicMock

import pytest

observability_stub = types.ModuleType("services.observability")
structured_logger_stub = types.ModuleType("services.observability.structured_logger")
structured_logger_stub.trace_id_ctx = ContextVar("trace_id", default="-")
sys.modules.setdefault("services.observability", observability_stub)
sys.modules.setdefault("services.observability.structured_logger", structured_logger_stub)

from core.protocols.worker_control import WsMessage, WsMessageType
from services.infra.worker_control_hub import WorkerConnection, WorkerControlHub

pytestmark = pytest.mark.anyio


def build_hub_with_worker() -> WorkerControlHub:
    WorkerControlHub._instance = None
    hub = WorkerControlHub()
    hub._workers["worker:test"] = WorkerConnection(
        worker_id="worker:test",
        worker_type="test",
        runtime_target="worker:test",
        websocket=MagicMock(),
        port=9999,
    )
    return hub


async def test_worker_control_handler_receives_binary_body_contract():
    hub = build_hub_with_worker()
    calls = []

    async def handler(worker_id, msg, binary_body=None):
        calls.append((worker_id, msg.type, binary_body))

    hub.on_message(WsMessageType.HEARTBEAT, handler)

    await hub._dispatch_message(
        "worker:test",
        WsMessage.heartbeat("worker:test", load=0.2),
        binary_body=b"payload",
    )

    assert calls == [("worker:test", WsMessageType.HEARTBEAT, b"payload")]


async def test_worker_control_handler_does_not_fallback_to_legacy_signature():
    hub = build_hub_with_worker()
    calls = []

    def legacy_handler(worker_id, msg):
        calls.append((worker_id, msg.type))

    hub.on_message(WsMessageType.HEARTBEAT, legacy_handler)

    await hub._dispatch_message(
        "worker:test",
        WsMessage.heartbeat("worker:test", load=0.2),
        binary_body=b"payload",
    )

    assert calls == []
