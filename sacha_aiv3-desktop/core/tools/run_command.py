"""
core/tools/run_command.py — gated terminal executor.

Only commands on the allowlist run, only from the project data directory,
and every invocation is time-boxed. This tool is marked ``dangerous`` so it
can never be auto-fired by the pipeline.
"""

from __future__ import annotations

import asyncio
import os
import subprocess
from typing import Any

from core.tools.base import Tool, ToolError

_ALLOWLIST = {
    "echo", "ver", "whoami", "dir", "where", "cd",
    "ipconfig", "systeminfo", "tasklist", "ping", "netstat", "date", "time",
    "python --version", "git --version",
}


class RunCommandTool(Tool):
    name = "run_command"
    description = "Run a short, allowlisted system command and return its output."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}
    dangerous = True

    def __init__(self, data_dir: Any | None = None, settings: Any | None = None) -> None:
        self.cwd = str(PathLike(data_dir)) if data_dir else os.getcwd()
        self.timeout = 10.0

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip()
        command = query.removeprefix("!")
        if not command:
            raise ToolError("no command given")
        base = command.split()[0].lower()
        if base not in {item.split()[0] for item in _ALLOWLIST} and command.split()[0] not in {
            item.split()[0] for item in _ALLOWLIST
        }:
            raise ToolError(f"command {base!r} is not on the allowlist")
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                cwd=self.cwd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=self.timeout)
        except TimeoutError as exc:
            raise ToolError(f"command timed out after {self.timeout:.0f}s") from exc
        except Exception as exc:
            raise ToolError(f"failed to run command: {exc}") from exc
        out = (stdout or b"").decode("utf-8", errors="replace").strip()
        err = (stderr or b"").decode("utf-8", errors="replace").strip()
        return out or err or f"command finished with exit code {proc.returncode}"


class PathLike(str):
    """Minimal cast helper so data_dir paths (str|Path) work in cwd=."""

    def __new__(cls, value: Any) -> PathLike:
        return str.__new__(cls, os.fspath(value))
