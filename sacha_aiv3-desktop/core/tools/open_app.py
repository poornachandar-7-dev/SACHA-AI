"""
core/tools/open_app.py — launch an app by friendly name (Windows-first).
"""

from __future__ import annotations

import asyncio
import os
import shutil
import subprocess
from typing import Any

from core.tools.base import Tool, ToolError

# Friendly names → launch strategy. Known Windows builtins use os.startfile
# (nothing to search), everything else falls back to PATH lookup.
_STARTFILE_APPS = {
    "notepad": "notepad.exe",
    "calculator": "calc.exe",
    "explorer": "explorer.exe",
    "cmd": "cmd.exe",
    "powershell": "powershell.exe",
    "paint": "mspaint.exe",
    "task manager": "taskmgr.exe",
    "control panel": "control.exe",
    "file explorer": "explorer.exe",
}


class OpenAppTool(Tool):
    name = "open_app"
    description = "Launch an application by name (notepad, calculator, …)."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, data_dir: Any | None = None, settings: Any | None = None) -> None:
        self.data_dir = data_dir or os.getcwd()

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        if not query:
            raise ToolError("no app name provided")
        key = query.lower()
        if key in _STARTFILE_APPS:
            await asyncio.to_thread(os.startfile, _STARTFILE_APPS[key])  # type: ignore[attr-defined]
            return f"Launched {_STARTFILE_APPS[key]}."
        # PATH lookup as a last resort.
        for candidate in key.split():
            found = shutil.which(candidate)
            if found:
                proc = subprocess.Popen([found], cwd=str(self.data_dir))
                if proc.poll() is None:
                    return f"Launched {found} (pid {proc.pid})."
        raise ToolError(f"could not find app {query!r}")
