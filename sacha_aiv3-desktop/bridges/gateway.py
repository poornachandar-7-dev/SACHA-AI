"""
bridges/gateway.py — config screen for active bridges + service lifecycle.

The gateway owns the shared ConversationInbox and the route that feeds
incoming bridge messages into the reply composer. Future: a HUD settings
panel where the user toggles bridges and enters tokens.
"""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable

from bridges.registry import BridgeRegistry

logger = logging.getLogger(__name__)


class BridgeGateway:
    """Lifecycle manager for all messaging bridges."""

    def __init__(self, registry: BridgeRegistry | None = None) -> None:
        self.registry = registry or BridgeRegistry()
        self._pump_task: asyncio.Task | None = None

    async def start_all(self) -> list[str]:
        """Start every configured bridge and begin pumping the inbox."""
        started = await self.registry.start_all()
        self._pump_task = asyncio.create_task(self._pump())
        logger.info("gateway running with bridges: %s", ", ".join(started) or "none")
        return started

    async def stop_all(self) -> None:
        await self.registry.stop_all()
        if self._pump_task is not None:
            self._pump_task.cancel()
            try:
                await self._pump_task
            except asyncio.CancelledError:
                pass
            self._pump_task = None

    async def _pump(self) -> None:
        while True:
            try:
                message = await self.registry.inbox.get()
                logger.info("bridge message from %s: %s", message.channel, message.text[:80])
                # Assigned by the boot layer so bridges can share the composer.
                handler = getattr(self.registry, "_message_handler", None)
                if handler is not None:
                    task = handler(message)
                    if asyncio.iscoroutine(task):
                        await task
            except asyncio.CancelledError:
                break
            except Exception:
                logger.exception("bridge pump handler failed")

    def set_message_handler(self, handler: Callable) -> None:
        self.registry._message_handler = handler
