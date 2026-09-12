"""
core/tools/screenshot.py — capture the screen with Pillow and save it.
"""

from __future__ import annotations

import asyncio
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from core.tools.base import Tool, ToolError


class ScreenshotTool(Tool):
    name = "screenshot"
    description = "Take a screenshot and save it into the data cache."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, data_dir: Any | None = None, settings: Any | None = None) -> None:
        base = Path(data_dir) if data_dir else Path.cwd() / "data"
        self.shots_dir = base / "cache" / "screenshots"
        self.shots_dir.mkdir(parents=True, exist_ok=True)

    async def run(self, **kwargs: Any) -> str:
        from PIL import ImageGrab

        try:
            image = await asyncio.to_thread(ImageGrab.grab)
        except Exception as exc:
            raise ToolError(f"screenshot failed: {exc}") from exc
        stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%S")
        path = self.shots_dir / f"screenshot_{stamp}.png"
        image.save(path)
        return f"Screenshot saved to {path}"
