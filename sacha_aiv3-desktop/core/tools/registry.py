"""
core/tools/registry.py — tool registry + permission flags + plugin host.

The registry is the single interception point for local capabilities. Tools
marked ``dangerous`` (exec, fs writes) are only invoked from explicit
``!tool`` calls, never auto-fired.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from core.tools.base import Tool, ToolResult

logger = logging.getLogger(__name__)


class ToolRegistry:
    """Name → Tool mapping with invocation safety."""

    def __init__(self) -> None:
        self._tools: dict[str, Tool] = {}
        self._order: list[str] = []

    def register(self, tool: Tool) -> Tool:
        if not isinstance(tool, Tool):
            raise TypeError(f"expected Tool, got {type(tool).__name__}")
        if tool.name not in self._tools:
            self._order.append(tool.name)
        self._tools[tool.name] = tool
        return tool

    def register_defaults(
        self,
        data_dir: Any | None = None,
        settings: Any | None = None,
    ) -> list[str]:
        """Register every built-in tool. Returns registered names."""
        from core.tools.clipboard import ClipboardTool
        from core.tools.open_app import OpenAppTool
        from core.tools.open_website import OpenWebsiteTool
        from core.tools.run_command import RunCommandTool
        from core.tools.screenshot import ScreenshotTool
        from core.tools.system_control import SystemControlTool
        from core.tools.weather import WeatherTool
        from core.tools.web_search import WebSearchTool

        for tool_cls in (
            OpenWebsiteTool,
            WebSearchTool,
            OpenAppTool,
            SystemControlTool,
            ClipboardTool,
            ScreenshotTool,
            RunCommandTool,
            WeatherTool,
        ):
            try:
                self.register(tool_cls(data_dir=data_dir, settings=settings))
            except Exception as exc:  # never let one tool block the rest
                logger.warning("failed to register %s: %s", tool_cls.__name__, exc)
        return list(self._tools)

    def get(self, name: str) -> Tool:
        try:
            return self._tools[name]
        except KeyError:
            raise KeyError(f"unknown tool {name!r} (available: {', '.join(self.names())})") from None

    def has(self, name: str) -> bool:
        return name in self._tools

    def names(self) -> list[str]:
        return list(self._order)

    def describe_all(self) -> list[dict[str, Any]]:
        return [self._tools[n].to_dict() for n in self._order]

    async def invoke(self, name: str, arguments: dict[str, Any] | None = None, timeout: float = 60.0) -> ToolResult:
        """Invoke a tool with a timeout; returns a normalised ToolResult."""
        tool = self.get(name)
        try:
            return await asyncio.wait_for(tool.invoke(arguments), timeout=timeout)
        except TimeoutError:
            logger.warning("tool %s timed out after %.1fs", name, timeout)
            return ToolResult(name=name, output=f"tool {name} timed out", ok=False, error="timeout")
        except Exception as exc:
            return ToolResult(name=name, output=str(exc), ok=False, error=str(exc))

    async def invoke_text(self, name: str, text: str, timeout: float = 60.0) -> ToolResult:
        """Invoke using the ``!name ARGS_STRING`` text protocol.

        Unknown structured args are passed through as a single ``query``
        argument, which every tolerant tool can accept.
        """
        result = await self.invoke(name, {"query": text}, timeout=timeout)
        result.name = name
        return result
