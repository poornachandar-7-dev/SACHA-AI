"""
Example plugin: weather lookup.

Demonstrates the plugin contract:
    run(action, payload, ctx) -> value

The loader validates plugin.json (requires the "network" permission here)
and isolates every call in the sandbox. Optional ``setup(ctx)`` can register
tools into the host's tool registry.
"""

from plugins.loader import PluginContext

MODEL = "example-plugins.weather"
HELP = "usage: run({'city': 'Paris'}) — returns current conditions."


def setup(ctx: PluginContext) -> None:
    ctx.logger.info("weather plugin ready — network permission granted")


def run(action: str, payload: dict, ctx: PluginContext) -> str:
    if action == "help":
        return HELP
    city = payload.get("city") or payload.get("query") or ""
    if not city:
        return "no city given — pass {\"city\": \"Paris\"}"
    if not ctx.can("network"):
        return "permission denied: 'network' is required"
    return f"[weather plugin] current conditions for {city}: see !weather for live data."


async def run_async(action: str, payload: dict, ctx: PluginContext) -> str:
    """Plugins may expose async run_async(); the loader prefers run()."""
    return run(action, payload, ctx)
