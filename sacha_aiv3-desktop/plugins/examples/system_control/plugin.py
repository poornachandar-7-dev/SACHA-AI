"""
Example plugin: system_control (volume / brightness).

Shows the "dangerous" permission path — 'exec' must be granted in plugin.json
and the sandbox enforces the timeout. Real implementation lives in the
built-in !system_control tool; this plugin exists to validate the pattern.
"""

import sys

from plugins.loader import PluginContext


def setup(ctx: PluginContext) -> None:
    ctx.logger.info("system_control plugin loaded — exec permission granted")


def run(action: str, payload: dict, ctx: PluginContext) -> str:
    if action == "help":
        return "actions: volume_up, volume_down, mute, brightness N"
    if not ctx.can("exec"):
        return "permission denied: 'exec' is required"
    if sys.platform != "win32":
        return "[system_control] non-Windows host — built-in tool handles it"
    return f"[system_control] action={action} payload={payload or {}} OK"
