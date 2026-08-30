import json
import logging
from typing import Any, AsyncGenerator, Dict, List

import httpx

from config.models import (
    POLLINATIONS_ANONYMOUS_CHAT_URL,
    POLLINATIONS_ANONYMOUS_MODELS_URL,
    POLLINATIONS_BASE_URL,
)
from core.interfaces.driver import BaseLLMDriver
from services.http_client import get_http_client

logger = logging.getLogger("PollinationsDriver")


class PollinationsDriver(BaseLLMDriver):
    def __init__(
        self,
        id: str = "pollinations",
        name: str = "Pollinations",
        description: str = "Pollinations OpenAI-compatible generation API",
    ):
        super().__init__(id, name, description)

    async def load(self):
        return None

    async def chat_completion(
        self,
        messages: list,
        model: str,
        temperature: float = 0.7,
        stream: bool = False,
        **kwargs,
    ) -> Any:
        url = self._chat_completion_url()
        headers = self._auth_headers()
        payload = self._completion_payload(
            messages=messages,
            model=model,
            temperature=temperature,
            stream=stream,
            kwargs=kwargs,
        )

        if stream:
            return self._stream_generator(url, payload, headers)
        return await self._fetch_non_stream(url, payload, headers)

    async def _fetch_non_stream(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> str:
        client = await get_http_client()
        try:
            response = await client.post(url, json=payload, headers=headers, timeout=120.0)
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"].get("content") or ""
        except httpx.HTTPStatusError as exc:
            detail = self._response_error_detail(exc.response)
            logger.error("Pollinations request failed: %s", detail)
            raise RuntimeError(detail) from exc
        except Exception as exc:
            logger.error("Pollinations request failed: %s", exc)
            raise

    async def _stream_generator(
        self,
        url: str,
        payload: Dict[str, Any],
        headers: Dict[str, str],
    ) -> AsyncGenerator[Dict[str, Any], None]:
        client = await get_http_client()
        try:
            async with client.stream(
                "POST",
                url,
                json=payload,
                headers=headers,
                timeout=120.0,
            ) as response:
                if response.status_code >= 400:
                    body = await response.aread()
                    detail = self._response_error_detail(response, body)
                    logger.error("Pollinations stream failed: %s", detail)
                    raise RuntimeError(detail)
                async for line in response.aiter_lines():
                    if not line.startswith("data:"):
                        continue

                    event = line.removeprefix("data:").strip()
                    if not event or event == "[DONE]":
                        continue

                    try:
                        data = json.loads(event)
                    except json.JSONDecodeError:
                        logger.debug(
                            "Skipping malformed Pollinations SSE event (%d chars)",
                            len(event),
                        )
                        continue

                    for choice in data.get("choices", []):
                        delta = choice.get("delta") or {}
                        content = delta.get("content") or ""
                        reasoning = delta.get("reasoning_content") or ""
                        tool_calls = delta.get("tool_calls") or []
                        if content or reasoning or tool_calls:
                            yield {
                                "content": content,
                                "reasoning": reasoning,
                                "tool_calls": tool_calls,
                            }
        except Exception as exc:
            logger.error("Pollinations stream failed: %s", exc)
            raise

    async def list_models(self) -> List[str]:
        client = await get_http_client()
        if not self._api_key():
            return await self._list_anonymous_models(client)

        url = f"{self._base_url()}/models"
        try:
            response = await client.get(url, headers=self._optional_auth_headers(), timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("Failed to list Pollinations models: %s", exc)
            return list(self.config.get("models") or [])

        models = []
        for item in data.get("data", []):
            model_id = item.get("id")
            if not model_id:
                continue

            endpoints = item.get("supported_endpoints") or []
            output_modalities = item.get("output_modalities") or []
            if "/v1/chat/completions" not in endpoints:
                continue
            if "text" not in output_modalities:
                continue

            models.append(model_id)

        return models

    async def _list_anonymous_models(self, client: httpx.AsyncClient) -> List[str]:
        try:
            response = await client.get(POLLINATIONS_ANONYMOUS_MODELS_URL, timeout=30.0)
            response.raise_for_status()
            data = response.json()
        except Exception as exc:
            logger.warning("Failed to list anonymous Pollinations models: %s", exc)
            return list(self.config.get("models") or [])

        models = []
        for item in data:
            model_name = item.get("name") if isinstance(item, dict) else None
            if not model_name:
                continue
            if item.get("tier") != "anonymous":
                continue
            if "text" not in (item.get("input_modalities") or []):
                continue
            if "text" not in (item.get("output_modalities") or []):
                continue
            if item.get("audio"):
                continue

            models.append(model_name)

        return models or list(self.config.get("models") or [])

    def _completion_payload(
        self,
        *,
        messages: list,
        model: str,
        temperature: float,
        stream: bool,
        kwargs: Dict[str, Any],
    ) -> Dict[str, Any]:
        payload = {
            "model": model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
        }
        payload.update({key: value for key, value in kwargs.items() if value is not None})
        return payload

    def _base_url(self) -> str:
        return (self.config.get("base_url") or POLLINATIONS_BASE_URL).rstrip("/")

    def _chat_completion_url(self) -> str:
        if not self._api_key():
            return POLLINATIONS_ANONYMOUS_CHAT_URL
        return f"{self._base_url()}/chat/completions"

    def _auth_headers(self) -> Dict[str, str]:
        api_key = self._api_key()
        headers = {"Content-Type": "application/json"}
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
        return headers

    def _optional_auth_headers(self) -> Dict[str, str]:
        api_key = self._api_key()
        return {"Authorization": f"Bearer {api_key}"} if api_key else {}

    def _api_key(self) -> str:
        api_key = str(self.config.get("api_key") or "").strip()
        return "" if api_key.lower() in {"none", "null"} else api_key

    def _response_error_detail(
        self,
        response: httpx.Response,
        body: bytes | None = None,
    ) -> str:
        try:
            payload = json.loads(body) if body is not None else response.json()
            detail = payload.get("error") or payload.get("detail") or payload
        except Exception:
            if body is not None:
                detail = body.decode("utf-8", errors="replace")
            else:
                detail = response.text
        return f"Pollinations Error {response.status_code}: {detail}"
