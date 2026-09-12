"""
core/tools — V2 tools.py equivalent, now a plugin host.
"""

from core.tools.base import Tool, ToolError, ToolResult
from core.tools.registry import ToolRegistry

__all__ = ["Tool", "ToolError", "ToolResult", "ToolRegistry"]
