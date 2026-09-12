"""
core/reply/streaming.py — async streaming responses to the HUD.

``TokenBus`` is a multicast fan-out: the reply pipeline publishes token
events and any number of subscribers (HUD window, CLI, smoke test) consume
them on their own pace without blocking the generator.
"""

from __future__ import annotations

import asyncio
import contextlib
from collections.abc import AsyncIterator
from dataclasses import dataclass
from typing import Any


@dataclass
class StreamEvent:
    kind: str  # "token" | "done" | "error"
    text: str = ""
    provider: str = ""
    meta: dict[str, Any] | None = None


class TokenBus:
    """Multicast async event bus for reply tokens."""

    def __init__(self, maxsize: int = 500) -> None:
        self._maxsize = maxsize
        self._subscribers: set[asyncio.Queue[StreamEvent]] = set()

    @contextlib.asynccontextmanager
    async def subscribe(self) -> AsyncIterator[asyncio.Queue[StreamEvent]]:
        queue: asyncio.Queue[StreamEvent] = asyncio.Queue(maxsize=self._maxsize)
        self._subscribers.add(queue)
        try:
            yield queue
        finally:
            self._subscribers.discard(queue)

    def publish(self, event: StreamEvent) -> None:
        for queue in list(self._subscribers):
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                # Slow consumer — drop oldest so streaming never stalls.
                try:
                    queue.get_nowait()
                except asyncio.QueueEmpty:
                    pass
                try:
                    queue.put_nowait(event)
                except asyncio.QueueEmpty:  # pragma: no cover
                    pass

    @property
    def subscriber_count(self) -> int:
        return len(self._subscribers)


async def pump_events(
    stream_gen: AsyncIterator[dict[str, Any]],
    bus: TokenBus,
) -> None:
    """Route composer.stream() events onto a TokenBus. Swallows errors."""
    try:
        async for event in stream_gen:
            kind = event.get("type", "token")
            bus.publish(
                StreamEvent(
                    kind=kind,
                    text=event.get("text", ""),
                    provider=event.get("provider", ""),
                    meta=event,
                )
            )
    except Exception:
        bus.publish(StreamEvent(kind="error", text="stream failed"))


async def collect(stream_gen: AsyncIterator[dict[str, Any]]) -> dict[str, Any]:
    """Utility that consumes a stream generator into a single result dict."""
    parts: list[str] = []
    done: dict[str, Any] = {}
    async for event in stream_gen:
        if event.get("type") == "token":
            parts.append(event.get("text", ""))
        elif event.get("type") == "done":
            done = event
        elif event.get("type") == "error":
            raise RuntimeError(event.get("message", "stream error"))
    done["result"] = "".join(parts)
    return done
