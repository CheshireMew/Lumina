from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from core.interfaces.module import CapabilityModule
from services.http_client import get_http_client


class Capability(CapabilityModule):
    async def search(self, query: str) -> str:
        api_key = self.config.get("api_key", "").strip()
        if not api_key:
            raise RuntimeError("Brave Search API key is not configured")

        count = int(self.config.get("count", 5) or 5)
        url = f"https://api.search.brave.com/res/v1/web/search?q={quote_plus(query)}&count={count}"

        client = await get_http_client()
        response = await client.get(
            url,
            headers={
                "Accept": "application/json",
                "X-Subscription-Token": api_key,
            },
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json() or {}

        results = ((payload.get("web") or {}).get("results") or [])[:count]
        if not results:
            return "No search results found."

        lines = []
        for item in results:
            title = item.get("title") or item.get("meta_url", {}).get("hostname") or "Untitled"
            description = item.get("description") or ""
            url = item.get("url") or ""
            lines.append(f"- {title}: {description} {url}".strip())
        return "\n".join(lines)

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "Brave Search",
                "description": "Web search provider backed by the Brave Search API.",
                "func_tag": "Search",
            }
        )
        return metadata
