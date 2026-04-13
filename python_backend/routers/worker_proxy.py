import logging
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from core.runtime import runtime_target_for_capability
from services.runtime_service import RuntimeService

logger = logging.getLogger("WorkerProxy")


def get_worker_control_url(capability: str, container) -> str:
    runtime_target = runtime_target_for_capability(capability)
    process_manager = container.get_process_manager()
    if process_manager and not process_manager.is_running(runtime_target):
        started = process_manager.start_worker(runtime_target)
        if not started:
            raise HTTPException(status_code=503, detail=f"{capability.upper()} worker failed to start")

    runtime = RuntimeService(container)
    snapshot = runtime.get_capability_runtime(capability, container.config.network.memory_url)
    upstream = snapshot.get("direct_base_url")
    if not upstream:
        raise HTTPException(status_code=503, detail=f"{capability.upper()} worker is unavailable")
    return upstream


async def proxy_json_request(
    capability: str,
    method: str,
    path: str,
    json_body: Optional[dict[str, Any]] = None,
    *,
    container,
):
    url = f"{get_worker_control_url(capability, container)}{path}"
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            if method == "GET":
                response = await client.get(url)
            elif method == "POST":
                response = await client.post(url, json=json_body)
            else:
                raise HTTPException(status_code=405, detail="Unsupported proxy method")
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail=f"{capability.upper()} worker offline") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"{capability.upper()} worker timeout") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Proxy failure for %s %s: %s", capability, url, exc)
        raise HTTPException(status_code=502, detail=f"{capability.upper()} upstream error") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response


async def proxy_multipart_request(
    capability: str,
    path: str,
    *,
    files: dict[str, tuple[str, bytes, str]],
    data: Optional[dict[str, Any]] = None,
    timeout: float = 60.0,
    container,
):
    url = f"{get_worker_control_url(capability, container)}{path}"
    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            response = await client.post(url, files=files, data=data or {})
    except httpx.ConnectError as exc:
        raise HTTPException(status_code=503, detail=f"{capability.upper()} worker offline") from exc
    except httpx.TimeoutException as exc:
        raise HTTPException(status_code=504, detail=f"{capability.upper()} worker timeout") from exc
    except HTTPException:
        raise
    except Exception as exc:
        logger.error("Multipart proxy failure for %s %s: %s", capability, url, exc)
        raise HTTPException(status_code=502, detail=f"{capability.upper()} upstream error") from exc

    if response.status_code >= 400:
        raise HTTPException(status_code=response.status_code, detail=response.text)

    return response
