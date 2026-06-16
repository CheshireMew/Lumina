import json
import logging
import re
from pathlib import Path
from typing import Dict, List, Optional

from core.interfaces.repository import ISessionRepository

logger = logging.getLogger("FileSessionRepository")


class FileSessionRepository(ISessionRepository):
    def __init__(self, root: Path):
        self.root = Path(root)
        self.root.mkdir(parents=True, exist_ok=True)

    def _session_key(self, user_id: str, char_id: str) -> str:
        safe_user = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(user_id)) or "default_user"
        safe_char = re.sub(r"[^a-zA-Z0-9_\-]", "_", str(char_id))
        if not safe_char:
            raise ValueError("char_id must be non-empty")
        return f"{safe_char}_{safe_user}"

    def _path_for_session(self, user_id: str, char_id: str) -> Path:
        return self.root / f"{self._session_key(user_id, char_id)}.json"

    async def get_session(self, user_id: str, char_id: str) -> Optional[Dict]:
        path = self._path_for_session(user_id, char_id)
        if not path.exists():
            return None

        try:
            with path.open("r", encoding="utf-8") as handle:
                return json.load(handle)
        except json.JSONDecodeError as exc:
            logger.error("Invalid session JSON at %s: %s", path, exc)
            return None

    async def save_session(self, user_id: str, char_id: str, data: Dict) -> bool:
        path = self._path_for_session(user_id, char_id)
        with path.open("w", encoding="utf-8") as handle:
            json.dump(data, handle, ensure_ascii=False, indent=2)
        return True

    async def delete_session(self, user_id: str, char_id: str) -> bool:
        path = self._path_for_session(user_id, char_id)
        if path.exists():
            path.unlink()
            return True
        return False

    async def get(self, id: str) -> Optional[Dict]:
        path = self.root / f"{self._safe_id(id)}.json"
        if not path.exists():
            return None
        with path.open("r", encoding="utf-8") as handle:
            return json.load(handle)

    async def save(self, entity: Dict) -> bool:
        session_id = entity.get("id")
        if not session_id:
            raise ValueError("Session entity must include an id.")
        path = self.root / f"{self._safe_id(session_id)}.json"
        with path.open("w", encoding="utf-8") as handle:
            json.dump(entity, handle, ensure_ascii=False, indent=2)
        return True

    async def delete(self, id: str) -> bool:
        path = self.root / f"{self._safe_id(id)}.json"
        if path.exists():
            path.unlink()
            return True
        return False

    async def get_recent(self, limit: int = 10) -> List[Dict]:
        files = sorted(self.root.glob("*.json"), key=lambda item: item.stat().st_mtime, reverse=True)
        sessions: List[Dict] = []
        for path in files[:limit]:
            try:
                with path.open("r", encoding="utf-8") as handle:
                    sessions.append(json.load(handle))
            except json.JSONDecodeError as exc:
                logger.error("Invalid session JSON at %s: %s", path, exc)
        return sessions

    def _safe_id(self, value: str) -> str:
        return re.sub(r"[^a-zA-Z0-9_\-]", "_", str(value)) or "session"
