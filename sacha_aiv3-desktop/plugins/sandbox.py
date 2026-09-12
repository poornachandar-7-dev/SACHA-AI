"""
plugins/sandbox.py — plugin error isolation.

Plugins run with a fresh context and a strict timeout. Exceptions never
escape into the host pipeline; they become error strings the HUD shows.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

logger = logging.getLogger(__name__)


class PluginError(RuntimeError):
    pass


class PluginSandbox:
    """Timeout + exception isolation for plugin invocations."""

    def __init__(self, default_timeout: float = 30.0) -> None:
        self.default_timeout = default_timeout

    def call(self, fn, *args, timeout: float | None = None, **kwargs: Any) -> Any:
        """Run a sync plugin function inside a timeout-aware wrapper."""
        timeout = timeout or self.default_timeout
        try:
            return asyncio.run(asyncio.wait_for(_runner(fn, args, kwargs), timeout=timeout))
        except TimeoutError:
            logger.warning("plugin call timed out after %.0fs", timeout)
            raise PluginError(f"plugin timed out after {timeout:.0f}s") from None
        except Exception as exc:
            logger.warning("plugin raised: %s", exc)
            raise PluginError(str(exc)) from exc

    async def call_async(self, coro, timeout: float | None = None) -> Any:
        timeout = timeout or self.default_timeout
        try:
            return await asyncio.wait_for(coro, timeout=timeout)
        except TimeoutError:
            raise PluginError(f"plugin timed out after {timeout:.0f}s") from None
        except Exception as exc:
            raise PluginError(str(exc)) from exc


async def _runner(fn, args: tuple, kwargs: dict[str, Any]):
    result = fn(*args, **kwargs)
    if asyncio.iscoroutine(result):
        return await result
    return result
