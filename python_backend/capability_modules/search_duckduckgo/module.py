from __future__ import annotations

from typing import Any
from urllib.parse import quote_plus

from core.interfaces.module import CapabilityModule
from services.http_client import get_http_client


class Capability(CapabilityModule):
    async def search(self, query: str) -> str:
        count = int(self.config.get("count", 5) or 5)
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

    def get_metadata(self) -> dict[str, Any]:
        metadata = super().get_metadata()
        metadata.update(
            {
                "name": "DuckDuckGo Search",
                "description": "Web search provider backed by DuckDuckGo instant answers.",
                "func_tag": "Search",
            }
        )
        return metadata
