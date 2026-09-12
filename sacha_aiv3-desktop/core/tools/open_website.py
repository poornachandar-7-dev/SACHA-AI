"""
core/tools/open_website.py — (V2 carry-over) open a URL in the default browser.
"""

from __future__ import annotations

import re
import webbrowser
from typing import Any

from core.tools.base import Tool, ToolError

_URL_RE = re.compile(r"(https?://[^\s]+|www\.[^\s]+|\b[\w.-]+\.[a-z]{2,}(?:/[^\s]*)?)", re.IGNORECASE)


class OpenWebsiteTool(Tool):
    name = "open_website"
    description = "Open a website or URL in the default browser."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, data_dir=None, settings=None, timeout: float = 10.0) -> None:
        self.timeout = timeout

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        match = _URL_RE.search(query)
        target = match.group(0) if match else ""
        if not target:
            raise ToolError("no URL found in request")
        if not target.startswith(("http://", "https://")):
            if target.startswith("www."):
                target = "https://" + target
            elif not any(target.startswith(host) for host in ("localhost",)):
                target = "https://" + target
        webbrowser.open(target, new=2)
        return f"Opened {target} in the default browser."
