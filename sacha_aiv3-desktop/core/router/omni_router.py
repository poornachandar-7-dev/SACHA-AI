"""
core/router/omni_router.py — automatic model selection.

Routes a message to the cheapest provider that can still answer it well:
privacy-sensitive work always goes local, simple chat prefers local, and
complex/research/code work prefers the first configured cloud provider.
"""

from __future__ import annotations

from collections.abc import AsyncIterator
from typing import Any

from core.providers.registry import ProviderRegistry
from core.router.classifier import KeywordClassifier, RoutingIntent


class OmniRouter:
    """Decides which provider answers a message, then dispatches to it."""

    def __init__(
        self,
        registry: ProviderRegistry,
        classifier: KeywordClassifier | None = None,
    ) -> None:
        self.registry = registry
        self.classifier = classifier or KeywordClassifier()

    # -- decision ----------------------------------------------------------
    def classify(self, text: str) -> RoutingIntent:
        return self.classifier.classify(text, available_tools=())

    def choose_provider(self, text: str) -> str:
        """Return the provider name that should answer ``text``."""
        intent = self.classify(text)
        return self._resolve(intent, text)

    def _resolve(self, intent: RoutingIntent, text: str) -> str:
        cloud = self.registry.cloud_chain()
        local_available = self.registry.has("local")

        if intent.privacy_sensitive or intent.provider_hint == "local":
            if local_available:
                return "local"
        if intent.complexity in ("complex", "moderate") and cloud:
            return cloud[0]
        # Simple chat or no cloud at all → local if present.
        if local_available:
            return "local"
        configured = self.registry.configured_names()
        return configured[0] if configured else "local"

    async def complete(
        self,
        text: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> tuple[str, str]:
        """Generate a full reply. Returns ``(text, provider_name)``."""
        name = self.choose_provider(text)
        provider = self.registry.get(name)
        reply = await provider.generate(messages, **kwargs)
        return reply, name

    async def stream(
        self,
        text: str,
        messages: list[dict[str, Any]],
        **kwargs: Any,
    ) -> AsyncIterator[tuple[str, str]]:
        """Yield ``(token, provider_name)`` fragments."""
        name = self.choose_provider(text)
        provider = self.registry.get(name)
        async for token in provider.stream(messages, **kwargs):
            yield token, name

    def describe(self) -> dict[str, Any]:
        """Snapshot of routing state (HUD status panel data)."""
        names = self.registry.configured_names()
        return {
            "configured_providers": names,
            "cloud": self.registry.cloud_chain(),
            "default": self.registry.get("local").model if self.registry.has("local") else None,
        }
