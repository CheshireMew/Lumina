from __future__ import annotations

import logging
import os
import threading
import time
from collections.abc import Callable


def _process_is_running(process_id: int) -> bool:
    if process_id <= 0:
        return False
    if os.name == "nt":
        import ctypes

        process_query_limited_information = 0x1000
        still_active = 259
        kernel32 = ctypes.windll.kernel32
        handle = kernel32.OpenProcess(
            process_query_limited_information,
            False,
            process_id,
        )
        if not handle:
            return False
        try:
            exit_code = ctypes.c_ulong()
            if not kernel32.GetExitCodeProcess(handle, ctypes.byref(exit_code)):
                return False
            return exit_code.value == still_active
        finally:
            kernel32.CloseHandle(handle)

    try:
        os.kill(process_id, 0)
        return True
    except (OSError, ProcessLookupError):
        return False


def start_parent_watchdog(
    request_shutdown: Callable[[], None],
    *,
    logger: logging.Logger | None = None,
    interval_seconds: float = 1.0,
) -> threading.Thread | None:
    raw_parent_id = os.environ.get("LUMINA_PARENT_PID", "").strip()
    if not raw_parent_id:
        return None
    try:
        parent_id = int(raw_parent_id)
    except ValueError:
        if logger:
            logger.warning("Ignoring invalid LUMINA_PARENT_PID=%r", raw_parent_id)
        return None
    if parent_id == os.getpid():
        return None

    def watch() -> None:
        while _process_is_running(parent_id):
            time.sleep(interval_seconds)
        if logger:
            logger.warning("Parent process %s exited; stopping owned runtime", parent_id)
        request_shutdown()

    thread = threading.Thread(
        target=watch,
        name=f"lumina-parent-watch-{parent_id}",
        daemon=True,
    )
    thread.start()
    return thread
