import asyncio
import logging
import queue
import uuid

from fastapi import WebSocket
from starlette.websockets import WebSocketDisconnect

from security.tokens import TokenManager

from .runtime_state import SttRuntimeState

logger = logging.getLogger("STTWebSocketHub")


class SttWebSocketHub:
    def __init__(self, state: SttRuntimeState):
        self._state = state

    async def handle(self, websocket: WebSocket):
        if not self._is_authorized(websocket):
            await websocket.close(code=1008, reason="Invalid stream token")
            return

        await websocket.accept()
        connection_id = str(uuid.uuid4())
        self._state.active_websockets[connection_id] = websocket

        if len(self._state.active_websockets) == 1 and self._state.audio_manager:
            if not self._state.audio_manager.is_running:
                self._state.audio_manager.start()
                self._drain_messages()

        try:
            sender = asyncio.create_task(self._sender_task())
            receiver = asyncio.create_task(self._receiver_task(websocket))
            done, pending = await asyncio.wait([sender, receiver], return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                task.result()
        finally:
            self._state.active_websockets.pop(connection_id, None)
            if (
                len(self._state.active_websockets) == 0
                and self._state.audio_manager
                and self._state.audio_manager.is_running
            ):
                self._state.audio_manager.stop()

    def _is_authorized(self, websocket: WebSocket) -> bool:
        token = websocket.query_params.get("token")
        if not token:
            return False

        try:
            payload = TokenManager.verify_token(token, expected_scope="worker_access")
            worker_id = getattr(websocket.app.state, "worker_id", None)
            return bool(payload and (not worker_id or payload.get("sub") == worker_id))
        except Exception:
            return False

    def _drain_messages(self) -> None:
        while not self._state.message_queue.empty():
            try:
                self._state.message_queue.get_nowait()
            except queue.Empty:
                break
            except Exception as exc:
                logger.debug("Queue drain error: %s", exc)
                break

    async def _sender_task(self):
        try:
            while True:
                if not self._state.message_queue.empty():
                    message = self._state.message_queue.get_nowait()
                    await self._broadcast(message)
                await asyncio.sleep(0.02)
        except WebSocketDisconnect:
            return
        except Exception as exc:
            logger.error("WS Sender Error: %s", exc)

    async def _broadcast(self, message: dict) -> None:
        stale_connection_ids: list[str] = []
        for connection_id, websocket in list(self._state.active_websockets.items()):
            try:
                await websocket.send_json(message)
            except Exception as exc:
                logger.debug("Dropping stale STT WebSocket %s: %s", connection_id, exc)
                stale_connection_ids.append(connection_id)

        for connection_id in stale_connection_ids:
            self._state.active_websockets.pop(connection_id, None)

    @staticmethod
    async def _receiver_task(websocket: WebSocket):
        try:
            while True:
                try:
                    await asyncio.wait_for(websocket.receive_text(), timeout=30.0)
                except asyncio.TimeoutError:
                    if websocket.client_state == 3:
                        raise WebSocketDisconnect()
        except WebSocketDisconnect:
            return
