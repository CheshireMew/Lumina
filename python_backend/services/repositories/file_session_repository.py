import asyncio
import json
import logging
import os
import re
import uuid
from pathlib import Path
from typing import Dict, List, Optional

from core.interfaces.repository import ISessionRepository
from services.companion.identity import DEFAULT_USER_ID

logger = logging.getLogger("FileSessionRepository")


class FileSessionRepository(ISessionRepository):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)
        self._locks: dict[Path, asyncio.Lock] = {}

    def _lock_for(self, path: Path) -> asyncio.Lock:
        return self._locks.setdefault(path, asyncio.Lock())

    def _session_key(self, user_id: str, char_id: str) -> str:
        safe_user = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(user_id)) or DEFAULT_USER_ID
        safe_char = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(char_id))
        if not safe_char:
            raise ValueError("char_id must be non-empty")
        return f"{safe_char}_{safe_user}"

    def _path_for_session(self, user_id: str, char_id: str) -> Path:
        return self.root / f"{self._session_key(user_id, char_id)}.json"

    async def get_session(self, user_id: str, char_id: str) -> Optional[Dict]:
        path = self._path_for_session(user_id, char_id)
        async with self._lock_for(path):
            if not await asyncio.to_thread(path.exists):
                return None
            try:
                return await asyncio.to_thread(self._read_json, path)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"Invalid session JSON at {path}: {exc}") from exc

    async def save_session(self, user_id: str, char_id: str, data: Dict) -> bool:
        path = self._path_for_session(user_id, char_id)
        async with self._lock_for(path):
            await asyncio.to_thread(self._write_json, path, data)
        return True

    async def delete_session(self, user_id: str, char_id: str) -> bool:
        path = self._path_for_session(user_id, char_id)
        async with self._lock_for(path):
            if await asyncio.to_thread(path.exists):
                await asyncio.to_thread(path.unlink)
                return True
            return False

    async def get(self, id: str) -> Optional[Dict]:
        path = self.root / f"{self._safe_id(id)}.json"
        async with self._lock_for(path):
            if not await asyncio.to_thread(path.exists):
                return None
            return await asyncio.to_thread(self._read_json, path)

    async def save(self, entity: Dict) -> bool:
        session_id = entity.get("id")
        if not session_id:
            raise ValueError("Session entity must include an id.")
        path = self.root / f"{self._safe_id(session_id)}.json"
        async with self._lock_for(path):
            await asyncio.to_thread(self._write_json, path, entity)
        return True

    async def delete(self, id: str) -> bool:
        path = self.root / f"{self._safe_id(id)}.json"
        async with self._lock_for(path):
            if await asyncio.to_thread(path.exists):
                await asyncio.to_thread(path.unlink)
                return True
            return False

    async def get_recent(self, limit: int = 10) -> List[Dict]:
        return await asyncio.to_thread(self._get_recent_sync, limit)

    def _safe_id(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", str(value)) or "session"

    @staticmethod
    def _write_json(path: Path, data: Dict) -> None:
        temp_path = path.with_name(f".{path.name}.{uuid.uuid4().hex}.tmp")
        with temp_path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)

    @staticmethod
    def _read_json(path: Path) -> Dict:
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    def _get_recent_sync(self, limit: int) -> List[Dict]:
        files = sorted(
            self.root.glob("*.json"),
            key=lambda item: item.stat().st_mtime,
            reverse=True,
        )
        sessions: List[Dict] = []
        for path in files[:limit]:
            try:
                sessions.append(self._read_json(path))
            except json.JSONDecodeError as exc:
                logger.error("Invalid session JSON at %s: %s", path, exc)
        return sessions
