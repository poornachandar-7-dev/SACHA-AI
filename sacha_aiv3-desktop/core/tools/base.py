"""
core/tools/base.py — Tool interface (name, schema, run).

Every tool exposes its own ``parameters`` JSON-schema so a future
function-calling integration can forward them to a model. Until then the
composer uses the explicit ``!toolname args`` protocol plus a few safe
auto-fire categories.
"""

from __future__ import annotations

import time
from abc import ABC
from dataclasses import dataclass
from typing import Any


@dataclass
class ToolResult:
    """Normalized outcome of an invocation."""

    name: str
    output: str
    ok: bool = True
    duration_ms: float = 0.0
    error: str | None = None

    def to_dict(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "output": self.output,
            "ok": self.ok,
            "duration_ms": round(self.duration_ms, 1),
            "error": self.error,
        }


class ToolError(RuntimeError):
    """Raised by Tool.run when the operation cannot complete."""


class Tool(ABC):
    """Base class for all built-in and plugin registered tools."""

    name: str = "tool"
    description: str = "A tool."
    parameters: dict[str, Any] = {}  # JSON-schema style
    dangerous: bool = False  # True for exec/fs mutation tools

    async def run(self, **kwargs: Any) -> str:
        """Execute the tool; return a human-readable string result.
        Raise :class:`ToolError` to signal a recoverable failure.
        """
        raise NotImplementedError

    async def invoke(self, arguments: dict[str, Any] | None = None) -> ToolResult:
        started = time.perf_counter()
        args = arguments or {}
        try:
            output = await self.run(**args)
            return ToolResult(
                name=self.name,
                output=output,
                duration_ms=(time.perf_counter() - started) * 1000,
            )
        except ToolError as exc:
            return ToolResult(
                name=self.name,
                output=str(exc),
                ok=False,
                duration_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )
        except Exception as exc:  # tools must never crash the pipeline
            return ToolResult(
                name=self.name,
                output=f"tool failed: {exc}",
                ok=False,
                duration_ms=(time.perf_counter() - started) * 1000,
                error=str(exc),
            )

    def to_dict(self) -> dict[str, str | dict]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": self.parameters,
            "dangerous": self.dangerous,
        }
