"""
core/providers/registry.py — provider lookup by name + capability.

The registry is the single place providers are registered and enumerated.
``register_defaults`` wires up every configured backend so the rest of the
system never import provider modules directly.
"""

from __future__ import annotations

from typing import Any

from core.providers.base import ModelProvider, ProviderError
from core.providers.gemini import GeminiProvider
from core.providers.local import LocalProvider
from core.providers.nvidia import NvidiaProvider
from core.providers.openai import OpenAIProvider


class ProviderRegistry:
    """Registered ModelProvider instances, keyed by ``provider.name``."""

    def __init__(self, settings: Any | None = None) -> None:
        self._settings = settings
        self._providers: dict[str, ModelProvider] = {}

    # -- registration ----------------------------------------------------
    def register(self, provider: ModelProvider) -> bool:
        """Register a provider instance. Returns True if it's the first."""
        if not isinstance(provider, ModelProvider):
            raise TypeError(f"expected ModelProvider, got {type(provider).__name__}")
        first = provider.name not in self._providers
        self._providers[provider.name] = provider
        return first

    def register_defaults(self) -> list[str]:
        """
        Register all built-in providers. Cloud providers are only registered
        when their API key is present in settings; local (Ollama) always is.
        Returns the list of registered names.
        """
        s = self._settings
        local = LocalProvider(
            model=getattr(s, "local_model", "llama3") if s else "llama3",
            base_url=getattr(s, "local_base_url", "http://localhost:11434") if s else None,
        )
        self.register(local)

        if s and getattr(s, "nvidia_api_key", None):
            self.register(NvidiaProvider(api_key=s.nvidia_api_key))
        if s and getattr(s, "openai_api_key", None):
            self.register(OpenAIProvider(api_key=s.openai_api_key))
        if s and getattr(s, "gemini_api_key", None):
            self.register(GeminiProvider(api_key=s.gemini_api_key))

        return self.names()

    def register_builtin(self, provider: ModelProvider) -> ModelProvider:
        """Convenience alias returning the registered provider (for chaining)."""
        self.register(provider)
        return provider

    # -- lookup -----------------------------------------------------------
    def get(self, name: str) -> ModelProvider:
        try:
            return self._providers[name]
        except KeyError:
            raise ProviderError(f"unknown provider {name!r}") from None

    def has(self, name: str) -> bool:
        return name in self._providers

    def __contains__(self, name: str) -> bool:
        return name in self._providers

    def all(self) -> list[ModelProvider]:
        return list(self._providers.values())

    def names(self) -> list[str]:
        return list(self._providers)

    def configured(self) -> list[ModelProvider]:
        """Providers that can actually answer right now."""
        return [p for p in self._providers.values() if p.configured]

    def configured_names(self) -> list[str]:
        return [p.name for p in self.configured()]

    def cloud_chain(self) -> list[str]:
        """Configured cloud providers in priority order."""
        return [p.name for p in self.configured() if not p.is_local]
