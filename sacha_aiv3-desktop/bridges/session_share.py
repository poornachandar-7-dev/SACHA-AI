"""
bridges/session_share.py — share session with desktop HUD.

The ConversationInbox is the mailbox every active bridge writes into. The
engine (via the gateway) reads it on the asyncio loop and routes incoming
messages through the normal ReplyComposer, so Telegram and the HUD truly
share one assistant brain.
"""

from __future__ import annotations

import asyncio
import logging

from bridges.base import BridgeMessage

logger = logging.getLogger(__name__)


class ConversationInbox:
    """Asyncio mailbox for inbound bridge messages."""

    def __init__(self, maxsize: int = 100) -> None:
        self._queue: asyncio.Queue[BridgeMessage] = asyncio.Queue(maxsize=maxsize)
        self._count = 0

    def submit(self, message: BridgeMessage) -> bool:
        try:
            self._queue.put_nowait(message)
            self._count += 1
            return True
        except asyncio.QueueFull:
            logger.warning("inbox full; dropping message from %s", message.channel)
            return False

    async def get(self) -> BridgeMessage:
        return await self._queue.get()

    async def drain(self, handler) -> None:
        """Run ``handler(message)`` for everything already queued."""
        while not self._queue.empty():
            await handler(await self._queue.get())

    @property
    def size(self) -> int:
        return self._queue.qsize()

    @property
    def total(self) -> int:
        return self._count

    def __repr__(self) -> str:  # pragma: no cover
        return f"<ConversationInbox queued={self.size()} total={self.total}>"
