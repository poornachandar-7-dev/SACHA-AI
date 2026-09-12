"""
core/tools/system_control.py — volume / brightness (Windows-first).

Volume uses the classic Win32 APPCOMMAND broadcast (works without admin):
volume up/down/mute via ``SendMessage(HWND_BROADCAST, WM_APPCOMMAND, ...)``.
Brightness needs the WMI monitor provider, which varies by machine, so it is
guarded and reports a clear error when unavailable.
"""

from __future__ import annotations

import asyncio
import ctypes
import platform
import re
import subprocess
import sys
from typing import Any

from core.tools.base import Tool, ToolError

HWND_BROADCAST = 0xFFFF
WM_APPCOMMAND = 0x0319
APPCOMMAND_VOLUME_UP = 0x0A
APPCOMMAND_VOLUME_DOWN = 0x09
APPCOMMAND_VOLUME_MUTE = 0x08
APPCOMMAND_BRIGHTNESS_UP = 0x1B
APPCOMMAND_BRIGHTNESS_DOWN = 0x1A


def _send_app_command(command: int) -> bool:
    if sys.platform != "win32":
        return False
    return bool(
        ctypes.windll.user32.SendMessageW(HWND_BROADCAST, WM_APPCOMMAND, 0, command << 16)
    )


_SET_BRIGHTNESS_PS = r"""
$startup = Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorBrightness -ErrorAction SilentlyContinue
if ($startup) {
    $methods = Get-CimInstance -Namespace root\wmi -ClassName WmiMonitorBrightnessMethods -ErrorAction SilentlyContinue
    if ($methods) { $methods.WmiSetBrightness(1, {value}) | Out-Null; Write-Output 'ok' }
}
"""


class SystemControlTool(Tool):
    name = "system_control"
    description = "Control system volume/brightness: volume up/down/mute, brightness N%."
    parameters = {"type": "object", "properties": {"query": {"type": "string"}}}

    def __init__(self, data_dir=None, settings=None) -> None:
        pass

    async def run(self, **kwargs: Any) -> str:
        query = str(kwargs.get("query", "")).strip().lower()
        if not query:
            raise ToolError("no control requested (try 'volume up', 'mute', 'brightness 50')")
        if "volume up" in query:
            return self._ok("volume up") if _send_app_command(APPCOMMAND_VOLUME_UP) else "volume control unavailable"
        if "volume down" in query:
            return self._ok("volume down") if _send_app_command(APPCOMMAND_VOLUME_DOWN) else "volume control unavailable"
        if "mute" in query:
            return self._ok("mute") if _send_app_command(APPCOMMAND_VOLUME_MUTE) else "volume control unavailable"
        m = re.search(r"brightness\s*(\d{1,3})", query)
        if m:
            value = min(100, max(0, int(m.group(1))))
            if sys.platform != "win32" or platform.machine().lower() != "amd64":
                raise ToolError("brightness control is Windows-only")
            ps = _SET_BRIGHTNESS_PS.replace("{value}", str(value))
            try:
                proc = await asyncio.create_subprocess_exec(
                    "powershell", "-NoProfile", "-Command", ps,
                    stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                )
                await proc.communicate()
                return f"Brightness set to {value}%."
            except Exception as exc:
                raise ToolError(f"brightness control failed: {exc}") from exc
        raise ToolError("unrecognised system command (volume up/down/mute, brightness N)")

    @staticmethod
    def _ok(action: str) -> str:
        return f"Performed '{action}'."
