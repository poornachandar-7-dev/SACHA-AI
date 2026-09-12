"""
core/tools/web_search.py — (V2 carry-over) DuckDuckGo HTML search (no API key).

Scrapes the lite HTML endpoint and returns the top results as text. This is
an MVP search tool; swapping in a real search API only changes this file.
"""

from __future__ import annotations

import asyncio
import re
from typing import Any

import httpx

from core.tools.base import Tool, ToolError

_Q = re.compile(r'href="(http[^"]+)"[^>]*>(.*?)</a>', re.DOTALL)
_TAG = re.compile(r"<[^>]+>")


class WebSearchTool(Tool):
    name = "web_search"
    description = "Search the web (DuckDuckGo) and return the top results."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, timeout: float = 15.0, data_dir: Any | None = None, settings: Any | None = None) -> None:
        self.timeout = timeout

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query or query.startswith("!"):  # bypass when only a tool name was given
            raise ToolError("no search query provided")
        url = "https://html.duckduckgo.com/html/"
        try:
            resp = await asyncio.wait_for(
                httpx.AsyncClient(timeout=self.timeout).get(url, params={"q": query}), self.timeout
            )
            resp.raise_for_status()
        except Exception as exc:
            raise ToolError(f"search failed: {exc}") from exc

        results: list[str] = []
        seen: set[str] = set()
        for href, label in _Q.findall(resp.text):
            title = _TAG.sub("", label).strip()
            if not title or "duckduckgo.com" in href or href in seen:
                continue
            seen.add(href)
            results.append(f"{title} — {href}")
            if len(results) >= 5:
                break
        if not results:
            return "No results found."
        return "\n".join(results)
