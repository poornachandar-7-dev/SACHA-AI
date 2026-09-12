"""
core/tools/clipboard.py — read/write the system clipboard via pyperclip.
"""

from __future__ import annotations

import asyncio
from typing import Any

from core.tools.base import Tool


class ClipboardTool(Tool):
    name = "clipboard"
    description = "Read or write the clipboard ('get' / 'copy <text>')."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, data_dir=None, settings=None) -> None:
        pass

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        import pyperclip

        def _copy(text: str) -> str:
            pyperclip.copy(text)
            return f"Copied {len(text)} characters to the clipboard."

        if query.lower() in ("get", "read", "paste"):
            return await asyncio.to_thread(pyperclip.paste) or "(clipboard is empty)"
        if query.lower().startswith(("copy ", "write ", "set ")):
            value = query.split(" ", 1)[1]
            return await asyncio.to_thread(_copy, value)
        # Default: interpret raw text as content to copy.
        return await asyncio.to_thread(_copy, query)
