from __future__ import annotations

import json
import os
import threading
import uuid
from pathlib import Path
from typing import Any, Callable


_LOCKS_GUARD = threading.Lock()
_LOCKS: dict[Path, threading.RLock] = {}


def _lock_for(path: Path) -> threading.RLock:
    resolved = path.resolve()
    with _LOCKS_GUARD:
        return _LOCKS.setdefault(resolved, threading.RLock())


class CharacterFileStore:
    """Shared locked JSON boundary for character config and module state."""

    def __init__(self, mutable_path: Path, seed_path: Path | None = None):
        self.mutable_path = Path(mutable_path)
        self.seed_path = Path(seed_path) if seed_path else None
        self._lock = _lock_for(self.mutable_path)

    def load(self) -> dict[str, Any]:
        with self._lock:
            path = self.mutable_path if self.mutable_path.exists() else self.seed_path
            if path is None or not path.exists():
                return {}
            with path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, dict):
                raise ValueError(f"Character JSON must be an object: {path}")
            return payload

    def save(self, payload: dict[str, Any]) -> None:
        with self._lock:
            self._write(payload)

    def update(
        self,
        transform: Callable[[dict[str, Any]], dict[str, Any]],
    ) -> dict[str, Any]:
        with self._lock:
            current = self.load()
            updated = transform(dict(current))
            if not isinstance(updated, dict):
                raise TypeError("Character JSON update must return an object")
            self._write(updated)
            return updated

    def _write(self, payload: dict[str, Any]) -> None:
        self.mutable_path.parent.mkdir(parents=True, exist_ok=True)
        temporary = self.mutable_path.with_name(
            f".{self.mutable_path.name}.{uuid.uuid4().hex}.tmp"
        )
        with temporary.open("w", encoding="utf-8") as handle:
            json.dump(payload, handle, indent=2, ensure_ascii=False)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(temporary, self.mutable_path)
