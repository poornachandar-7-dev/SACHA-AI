"""
core/router/fallback.py — provider fallback chain (cloud -> local on failure).

Wraps the registry so any provider failure is retried against the next
provider in the chain instead of crashing the request. Full replies fall
back mid-request; streaming only falls back until the first token arrives
(because you cannot rewind a token stream).
"""

from __future__ import annotations

import logging
from collections.abc import AsyncIterator
from typing import Any

from core.providers.base import ProviderError
from core.providers.registry import ProviderRegistry

logger = logging.getLogger(__name__)


class FallbackChain:
    """Try providers in order until one answers."""

    def __init__(self, registry: ProviderRegistry) -> None:
        self.registry = registry

    def order(self, preferred: str | None = None) -> list[str]:
        """Configured providers in attempt order: preferred, then cloud, then local."""
        names = list(self.registry.configured_names())
        if preferred and preferred in names:
            names.remove(preferred)
            names.insert(0, preferred)
        ordered: list[str] = []
        if names and names[0] == preferred:
            ordered.append(names.pop(0))
        # Any remaining cloud providers first…
        ordered += [n for n in names if not self.registry.get(n).is_local]
        # …then local as the last line of defence.
        ordered += [n for n in names if self.registry.get(n).is_local]
        return ordered or list(self.registry.names())

    async def complete(
        self,
        preferred: str | None,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> tuple[str, str]:
        """Return ``(reply_text, provider_name)``, falling back on failure."""
        last_error: Exception | None = None
        for name in self.order(preferred):
            provider = self.registry.get(name)
            try:
                reply = await provider.generate(messages, **kwargs)
                return reply, name
            except ProviderError as exc:
                last_error = exc
                logger.warning("provider %s failed (%s); trying next", name, exc)
        raise ProviderError(
            f"all providers failed; last error: {last_error}"
        ) from last_error

    async def stream(
        self,
        preferred: str | None,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[tuple[str, str]]:
        """Yield ``(token, provider_name)``; falls back before first token only."""
        for name in self.order(preferred):
            provider = self.registry.get(name)
            started = False
            try:
                async for token in provider.stream(messages, **kwargs):
                    started = True
                    yield token, name
                return
            except ProviderError as exc:
                if started:
                    raise
                logger.warning("provider %s stream failed pre-token (%s); trying next", name, exc)
        raise ProviderError("all providers failed")
