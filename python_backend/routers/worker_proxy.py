import asyncio
import logging
import time
from typing import Any, Optional

import httpx
from fastapi import HTTPException

from core.runtime import runtime_target_for_capability, runtime_target_to_worker_id
from routers.deps import build_runtime_service
from services.http_client import get_http_client

logger = logging.getLogger("WorkerProxy")


async def get_worker_control_url(capability: str, container) -> str:
    runtime_registry = container.get_worker_runtime_registry()
    definition = runtime_registry.runtime_for_capability(capability)
    if definition:
        snapshot = runtime_registry.resolve(definition.id)
        if not snapshot or snapshot.status != "ready":
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "worker_runtime_unavailable",
                    "capability": capability,
                    "runtimeId": definition.id,
                    "displayName": definition.display_name,
                    "status": snapshot.status if snapshot else "unavailable",
                },
            )

    runtime_target = runtime_target_for_capability(capability)
    process_manager = container.get_process_manager()
    process_running = process_manager.is_running(runtime_target)
    if process_running:
        worker_id = runtime_target_to_worker_id(runtime_target)
        worker_node = container.get_worker_discovery().get_node(worker_id)
        if worker_node is not None:
            return worker_node.base_url
    else:
        started = await asyncio.to_thread(process_manager.start_worker, runtime_target)
        if not started:
            raise HTTPException(
                status_code=503,
                detail={
                    "code": "worker_start_failed",
                    "capability": capability,
                },
            )

    runtime = build_runtime_service(container)
    deadline = time.monotonic() + 30.0
    upstream = None
    client = await get_http_client()
    while time.monotonic() < deadline:
        snapshot = runtime.get_capability_runtime(
            capability,
            container.get_config().network.core_url,
        )
        upstream = snapshot.get("direct_base_url")
        if upstream:
            try:
                response = await client.get(f"{upstream}/health", timeout=2.0)
                if response.status_code < 500:
                    break
            except (httpx.ConnectError, httpx.TimeoutException):
                pass
        if not process_manager.is_running(runtime_target):
            upstream = None
            break
        await asyncio.sleep(0.25)
    else:
        upstream = None

    if not upstream:
        raise HTTPException(
            status_code=503,
            detail={
                "code": "worker_start_timeout",
                "capability": capability,
            },
        )
    return upstream


async def proxy_json_request(
    capability: str,
    method: str,
    path: str,
    json_body: Optional[dict[str, Any]] = None,
    *,
    container,
):
    url = f"{await get_worker_control_url(capability, container)}{path}"
    try:
        client = await get_http_client()
        if method == "GET":
            response = await client.get(url, timeout=10.0)
        elif method == "POST":
            response = await client.post(url, json=json_body, timeout=10.0)
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
    url = f"{await get_worker_control_url(capability, container)}{path}"
    try:
        client = await get_http_client()
        response = await client.post(
            url,
            files=files,
            data=data or {},
            timeout=timeout,
        )
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
