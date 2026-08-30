from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from services.http_client import get_http_client
from core.interfaces.search import SearchProvider


class BraveSearchProvider(SearchProvider):
    id = "driver.tool.search.brave"
    name = "Brave Search"
    description = "Web search provider backed by the Brave Search API."

    def __init__(self, config: Any):
        self.config = config

    async def search(self, query: str) -> str:
        settings = self.config.get_provider_settings(self.id)
        api_key = str(settings.get("api_key") or "").strip()
        if not api_key:
            raise RuntimeError("Brave Search API key is not configured")

        count = int(settings.get("count", 5) or 5)
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
            item_url = item.get("url") or ""
            lines.append(f"- {title}: {description} {item_url}".strip())
        return "\n".join(lines)


class DuckDuckGoSearchProvider(SearchProvider):
    id = "driver.tool.search.duckduckgo"
    name = "DuckDuckGo Search"
    description = "Web search provider backed by DuckDuckGo instant answers."

    def __init__(self, config: Any):
        self.config = config

    async def search(self, query: str) -> str:
        count = int(self.config.get_provider_settings(self.id).get("count", 5) or 5)
        client = await get_http_client()

        response = await client.get(
            f"https://api.duckduckgo.com/?q={quote_plus(query)}&format=json&no_html=1&skip_disambig=1",
            timeout=20.0,
        )
        response.raise_for_status()
        payload = response.json() or {}

        lines: list[str] = []
        abstract = payload.get("AbstractText")
        abstract_url = payload.get("AbstractURL")
        if abstract:
            lines.append(f"- Summary: {abstract} {abstract_url or ''}".strip())

        related = payload.get("RelatedTopics") or []
        for item in related:
            if "Topics" in item:
                for topic in item.get("Topics") or []:
                    text = topic.get("Text")
                    url = topic.get("FirstURL")
                    if text:
                        lines.append(f"- {text} {url or ''}".strip())
                    if len(lines) >= count:
                        break
            else:
                text = item.get("Text")
                url = item.get("FirstURL")
                if text:
                    lines.append(f"- {text} {url or ''}".strip())
            if len(lines) >= count:
                break

        if not lines:
            return "No search results found."
        return "\n".join(lines[:count])
